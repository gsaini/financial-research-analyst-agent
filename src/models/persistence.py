"""
Persistence Models (Phase 3.4).

SQLAlchemy ORM models for storing analyses, portfolios, watchlists,
and analysis history. Uses SQLite by default, PostgreSQL in production.

Usage::

    from src.models.persistence import get_session, Watchlist, AnalysisHistory
    session = get_session()
    session.add(Watchlist(user_id="session_123", symbol="AAPL"))
    session.commit()
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Text, JSON,
    Boolean, ForeignKey, Index, create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase, Session, sessionmaker, relationship,
)

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Base ─────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


# ── Models ───────────────────────────────────────────────────


class UserSession(Base):
    """Session-based user identification (no full auth)."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    preferences = Column(JSON, default=dict)

    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("AnalysisHistory", back_populates="user", cascade="all, delete-orphan")


class Watchlist(Base):
    """User watchlist — tracks symbols a user is monitoring."""
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), ForeignKey("user_sessions.session_id"), nullable=False)
    symbol = Column(String(10), nullable=False)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, default="")
    alert_above = Column(Float, nullable=True)
    alert_below = Column(Float, nullable=True)

    user = relationship("UserSession", back_populates="watchlists")

    __table_args__ = (
        Index("ix_watchlist_user_symbol", "user_id", "symbol", unique=True),
    )


class Portfolio(Base):
    """User portfolio definition."""
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), ForeignKey("user_sessions.session_id"), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("UserSession", back_populates="portfolios")
    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioHolding(Base):
    """Individual holding within a portfolio."""
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(10), nullable=False)
    shares = Column(Float, default=0)
    cost_basis = Column(Float, default=0)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    portfolio = relationship("Portfolio", back_populates="holdings")


class AnalysisHistory(Base):
    """Stored analysis results for comparison over time."""
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), ForeignKey("user_sessions.session_id"), nullable=False)
    symbol = Column(String(10), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)  # comprehensive, technical, dcf, etc.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    recommendation = Column(String(20), default="HOLD")
    confidence = Column(Float, default=0.5)
    current_price = Column(Float, default=0)
    target_price = Column(Float, nullable=True)
    results = Column(JSON, default=dict)  # Full analysis results
    summary = Column(Text, default="")

    user = relationship("UserSession", back_populates="analyses")

    __table_args__ = (
        Index("ix_analysis_user_symbol", "user_id", "symbol"),
    )


# ── Database Engine & Session ────────────────────────────────

_engine = None
_SessionFactory = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        from src.config import settings
        _engine = create_engine(
            settings.database.database_url,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def init_db():
    """Create all tables if they don't exist."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database tables created/verified")


def get_session() -> Session:
    """Get a new database session."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory()


# ── Convenience Functions ────────────────────────────────────


def get_or_create_user(session_id: str) -> UserSession:
    """Get existing user session or create a new one."""
    session = get_session()
    user = session.query(UserSession).filter_by(session_id=session_id).first()
    if not user:
        user = UserSession(session_id=session_id)
        session.add(user)
        session.commit()
    else:
        user.last_active = datetime.now(timezone.utc)
        session.commit()
    return user


def add_to_watchlist(session_id: str, symbol: str, notes: str = "") -> Dict:
    """Add a symbol to user's watchlist."""
    session = get_session()
    get_or_create_user(session_id)

    existing = session.query(Watchlist).filter_by(
        user_id=session_id, symbol=symbol.upper()
    ).first()
    if existing:
        return {"status": "already_exists", "symbol": symbol}

    item = Watchlist(user_id=session_id, symbol=symbol.upper(), notes=notes)
    session.add(item)
    session.commit()
    return {"status": "added", "symbol": symbol}


def get_watchlist(session_id: str) -> list:
    """Get user's watchlist."""
    session = get_session()
    items = session.query(Watchlist).filter_by(user_id=session_id).all()
    return [{"symbol": w.symbol, "added_at": w.added_at.isoformat(), "notes": w.notes} for w in items]


def remove_from_watchlist(session_id: str, symbol: str) -> Dict:
    """Remove a symbol from watchlist."""
    session = get_session()
    item = session.query(Watchlist).filter_by(
        user_id=session_id, symbol=symbol.upper()
    ).first()
    if item:
        session.delete(item)
        session.commit()
        return {"status": "removed", "symbol": symbol}
    return {"status": "not_found", "symbol": symbol}


def save_analysis(
    session_id: str,
    symbol: str,
    analysis_type: str,
    results: dict,
    recommendation: str = "HOLD",
    confidence: float = 0.5,
    current_price: float = 0,
    summary: str = "",
) -> int:
    """Save an analysis result to history. Returns the record ID."""
    session = get_session()
    get_or_create_user(session_id)

    record = AnalysisHistory(
        user_id=session_id,
        symbol=symbol.upper(),
        analysis_type=analysis_type,
        recommendation=recommendation,
        confidence=confidence,
        current_price=current_price,
        results=results,
        summary=summary,
    )
    session.add(record)
    session.commit()
    return record.id


def get_analysis_history(
    session_id: str,
    symbol: Optional[str] = None,
    limit: int = 20,
) -> list:
    """Get analysis history, optionally filtered by symbol."""
    session = get_session()
    query = session.query(AnalysisHistory).filter_by(user_id=session_id)
    if symbol:
        query = query.filter_by(symbol=symbol.upper())
    records = query.order_by(AnalysisHistory.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "type": r.analysis_type,
            "recommendation": r.recommendation,
            "confidence": r.confidence,
            "price": r.current_price,
            "created_at": r.created_at.isoformat(),
            "summary": r.summary,
        }
        for r in records
    ]


# Type hint for functions above that return Dict
from typing import Dict
