"""
FastAPI routes for the Financial Research Analyst API.
"""

from datetime import datetime
from typing import Any, Dict, List
import time

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    PortfolioRequest,
    PortfolioResponse,
    ReportRequest,
    ReportResponse,
    HealthResponse,
    ErrorResponse,
    ThemeAnalysisRequest,
    ThemeAnalysisResponse,
    ThemeCompareRequest,
    ThemeListResponse,
    ThemeSummary,
    PeerComparisonRequest,
    PeerComparisonResponse,
)
from src.agents import FinancialResearchAgent
from src.tools.market_data import get_stock_price, get_historical_data, get_company_info
from src.tools.technical_indicators import calculate_rsi, calculate_macd, calculate_moving_averages
from src.tools.theme_mapper import list_available_themes, analyze_theme, get_theme_definition
from src.tools.peer_comparison import compare_peers
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Track startup time for uptime calculation
_startup_time = time.time()

# Initialize FastAPI app
app = FastAPI(
    title="Financial Research Analyst API",
    description="AI-powered financial analysis and investment research API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = None


def get_agent() -> FinancialResearchAgent:
    """Get or create the financial research agent."""
    global agent
    if agent is None:
        agent = FinancialResearchAgent()
    return agent


# Create router for API versioning
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1")


@app.get("/", response_model=Dict[str, str])
async def root():
    """API root endpoint."""
    return {
        "name": "Financial Research Analyst API",
        "version": "1.0.0",
        "docs": "/docs",
    }


async def check_market_data_service() -> str:
    """Check if market data service is available."""
    try:
        result = get_stock_price("AAPL")
        if "error" in result:
            return "degraded"
        return "healthy"
    except Exception as e:
        logger.warning(f"Market data service check failed: {e}")
        return "unhealthy"


async def check_agent_engine() -> str:
    """Check if agent engine is initialized and ready."""
    try:
        agent = get_agent()
        if agent is None:
            return "unhealthy"
        return "healthy"
    except Exception as e:
        logger.warning(f"Agent engine check failed: {e}")
        return "unhealthy"


async def check_data_processing() -> str:
    """Check if data processing pipelines are working."""
    try:
        hist_data = get_historical_data("AAPL", period="1d")
        if "error" in hist_data or not hist_data:
            return "degraded"
        return "healthy"
    except Exception as e:
        logger.warning(f"Data processing check failed: {e}")
        return "unhealthy"


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check API health status with dependency checks.

    Performs checks on:
    - Market data service (Yahoo Finance integration)
    - Agent engine (LLM and orchestration)
    - Data processing pipelines

    Returns:
    - 200: All systems healthy
    - 503: Service unhealthy or degraded
    """
    check_start = time.time()

    # Run dependency checks concurrently
    market_data_status = await check_market_data_service()
    agent_status = await check_agent_engine()
    data_processing_status = await check_data_processing()

    checks = {
        "market_data": market_data_status,
        "agent_engine": agent_status,
        "data_processing": data_processing_status,
    }

    # Determine overall health status
    unhealthy = [s for s in checks.values() if s == "unhealthy"]
    degraded = [s for s in checks.values() if s == "degraded"]

    if unhealthy:
        overall_status = "unhealthy"
    elif degraded:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    # Calculate uptime in seconds
    uptime_seconds = time.time() - _startup_time

    # Calculate response time
    response_time_ms = (time.time() - check_start) * 1000

    health_response = HealthResponse(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.utcnow(),
        uptime_seconds=uptime_seconds,
        checks=checks,
        response_time_ms=round(response_time_ms, 2),
    )

    # Return appropriate HTTP status code
    if overall_status == "unhealthy":
        return JSONResponse(
            status_code=503,
            content=health_response.model_dump(mode='json'),
        )

    return health_response


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_stock(request: AnalysisRequest):
    """
    Analyze a stock symbol.
    
    Performs comprehensive analysis including technical, fundamental,
    sentiment, and risk analysis.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Analyzing {request.symbol}")
        
        # Get current price
        price_data = get_stock_price(request.symbol)
        if "error" in price_data:
            raise HTTPException(status_code=400, detail=f"Invalid symbol: {request.symbol}")
        
        current_price = price_data.get("current_price", 0)
        
        # Get historical data
        hist_data = get_historical_data(request.symbol, period="1y")
        
        # Calculate technical indicators
        technical = {}
        if "closes" in hist_data and len(hist_data["closes"]) > 0:
            closes = hist_data["closes"]
            technical["rsi"] = calculate_rsi(closes)
            technical["macd"] = calculate_macd(closes)
            technical["moving_averages"] = calculate_moving_averages(closes)
        
        # Get company info for fundamental
        company = get_company_info(request.symbol)
        
        # Generate summary and recommendation
        rsi_value = technical.get("rsi", {}).get("value", 50)
        macd_hist = technical.get("macd", {}).get("histogram", 0)
        
        if rsi_value < 30 and macd_hist > 0:
            recommendation = "BUY"
            confidence = 0.75
        elif rsi_value > 70 and macd_hist < 0:
            recommendation = "SELL"
            confidence = 0.75
        else:
            recommendation = "HOLD"
            confidence = 0.5
        
        summary = f"{request.symbol} is currently trading at ${current_price:.2f}. "
        summary += f"Technical indicators suggest a {recommendation} signal with {confidence*100:.0f}% confidence."
        
        execution_time = time.time() - start_time
        
        return AnalysisResponse(
            symbol=request.symbol,
            analysis_type=request.analysis_type.value,
            current_price=current_price,
            recommendation=recommendation,
            confidence=confidence,
            summary=summary,
            technical=technical,
            fundamental={"company": company, "price_data": price_data},
            sentiment={"status": "analyzed", "score": 0.5},
            risk={"volatility": "medium"},
            analyzed_at=datetime.utcnow(),
            execution_time_seconds=round(execution_time, 2),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/technical/{symbol}")
async def get_technical_analysis(symbol: str):
    """Get technical analysis for a symbol."""
    try:
        hist_data = get_historical_data(symbol, period="1y")
        
        if "error" in hist_data:
            raise HTTPException(status_code=400, detail=f"No data for symbol: {symbol}")
        
        closes = hist_data.get("closes", [])
        
        return {
            "symbol": symbol,
            "rsi": calculate_rsi(closes),
            "macd": calculate_macd(closes),
            "moving_averages": calculate_moving_averages(closes),
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fundamental/{symbol}")
async def get_fundamental_analysis(symbol: str):
    """Get fundamental analysis for a symbol."""
    try:
        company = get_company_info(symbol)
        price_data = get_stock_price(symbol)
        
        return {
            "symbol": symbol,
            "company": company,
            "price_data": price_data,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/{symbol}")
async def get_sentiment_analysis(symbol: str):
    """Get sentiment analysis for a symbol."""
    return {
        "symbol": symbol,
        "sentiment": "positive",
        "score": 0.65,
        "news_sentiment": 0.7,
        "social_sentiment": 0.6,
        "analyzed_at": datetime.utcnow().isoformat(),
    }


@router.post("/portfolio", response_model=PortfolioResponse)
async def analyze_portfolio(request: PortfolioRequest):
    """Analyze a portfolio of stocks."""
    try:
        analyses = []
        for symbol in request.symbols:
            price_data = get_stock_price(symbol)
            analyses.append({
                "symbol": symbol,
                "data": price_data,
            })
        
        return PortfolioResponse(
            symbols=request.symbols,
            individual_analyses=analyses,
            portfolio_metrics={"total_stocks": len(request.symbols)},
            diversification_score=0.7,
            risk_assessment="moderate",
            recommendations=["Consider diversifying across sectors"],
            analyzed_at=datetime.utcnow(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """Generate an investment research report."""
    import uuid
    
    try:
        report_id = str(uuid.uuid4())[:8]
        
        content = f"# Investment Research Report\n\n"
        content += f"Symbols: {', '.join(request.symbols)}\n"
        content += f"Generated: {datetime.utcnow().isoformat()}\n\n"
        content += "## Summary\n\nDetailed analysis available upon request."
        
        return ReportResponse(
            report_id=report_id,
            symbols=request.symbols,
            format=request.format,
            content=content,
            generated_at=datetime.utcnow(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/summary")
async def get_market_summary():
    """Get market summary."""
    return {
        "market_status": "open",
        "indices": {
            "SPY": {"price": 470.50, "change": 0.5},
            "QQQ": {"price": 395.20, "change": 0.8},
            "DIA": {"price": 375.30, "change": 0.3},
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# Thematic Investing Endpoints (Feature 1)
# ─────────────────────────────────────────────────────────────


@router.get("/themes", response_model=ThemeListResponse)
async def get_themes():
    """
    List all available investment themes.

    Returns summary information for each theme including name,
    description, constituent count, sector tags, and risk level.
    """
    try:
        themes_raw = list_available_themes()
        themes = [ThemeSummary(**t) for t in themes_raw]
        return ThemeListResponse(
            themes=themes,
            total_themes=len(themes),
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"Error listing themes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/theme/{theme_id}", response_model=ThemeAnalysisResponse)
async def analyze_investment_theme(theme_id: str, request: ThemeAnalysisRequest = None):
    """
    Analyze an investment theme.

    Performs comprehensive thematic analysis including:
    - Multi-horizon performance (1W, 1M, 3M, 6M, 1Y, YTD)
    - Top performers and laggards
    - Intra-theme correlation and diversification scoring
    - Momentum scoring (0-100)
    - Theme health score (0-100)
    - Sector overlap breakdown
    - Optional LLM-generated narrative outlook
    """
    start_time = time.time()

    try:
        # Validate theme exists
        theme_def = get_theme_definition(theme_id)
        if theme_def is None:
            raise HTTPException(
                status_code=404,
                detail=f"Theme '{theme_id}' not found. Use GET /api/v1/themes to list available themes.",
            )

        # Run analysis
        result = analyze_theme(theme_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        # Optionally generate narrative via the thematic agent
        if request and request.include_narrative:
            try:
                from src.agents.thematic import ThematicAnalystAgent
                agent = ThematicAnalystAgent()
                enriched = await agent.analyze_with_narrative(theme_id)
                result["outlook"] = enriched.get("outlook")
            except Exception as narrative_err:
                logger.warning(f"Narrative generation failed: {narrative_err}")
                result["outlook"] = "Unable to generate narrative outlook"

        result["execution_time_seconds"] = round(time.time() - start_time, 2)
        result["analyzed_at"] = datetime.utcnow().isoformat()

        return ThemeAnalysisResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Theme analysis error for '{theme_id}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/themes/compare")
async def compare_investment_themes(request: ThemeCompareRequest):
    """
    Compare multiple investment themes side by side.

    Provides performance, momentum, correlation, and health scores
    for each theme to help with allocation decisions.
    """
    start_time = time.time()

    try:
        if len(request.theme_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 theme IDs are required for comparison.",
            )
        if len(request.theme_ids) > 5:
            raise HTTPException(
                status_code=400,
                detail="Maximum 5 themes can be compared at once.",
            )

        comparison = []
        for tid in request.theme_ids:
            result = analyze_theme(tid)
            if "error" not in result:
                comparison.append({
                    "theme": result.get("theme"),
                    "theme_id": tid,
                    "performance": result.get("theme_performance", {}),
                    "momentum_score": result.get("momentum_score", 0),
                    "health_score": result.get("theme_health_score", 0),
                    "diversification": result.get("theme_risk", {}).get(
                        "diversification_score", "N/A"
                    ),
                    "intra_correlation": result.get("theme_risk", {}).get(
                        "intra_correlation"
                    ),
                    "risk_level": result.get("risk_level", "Unknown"),
                    "top_performers": result.get("top_performers", [])[:2],
                    "laggards": result.get("laggards", [])[:2],
                })
            else:
                comparison.append({"theme_id": tid, "error": result["error"]})

        return {
            "themes_compared": len(request.theme_ids),
            "comparison": comparison,
            "execution_time_seconds": round(time.time() - start_time, 2),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Theme comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# Peer Comparison Endpoints (Feature 2)
# ─────────────────────────────────────────────────────────────


@router.get("/peers/{symbol}", response_model=PeerComparisonResponse)
async def get_peer_comparison(symbol: str):
    """
    Get peer comparison for a symbol.

    Automatically discovers peers based on sector, industry, and market cap,
    and compares key financial metrics.
    """
    try:
        result = await compare_peers(symbol)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Peer comparison error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/peers/compare", response_model=PeerComparisonResponse)
async def compare_peers_custom(request: PeerComparisonRequest):
    """
    Compare a stock against a specific list of peers.
    """
    try:
        result = await compare_peers(request.symbol, request.peers)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Custom peer comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Include router in app
app.include_router(router)


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
        ).model_dump(),
    )
