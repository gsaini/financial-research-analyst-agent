"""
API Security Middleware (Phase 3.5).

Provides:
- API key authentication via X-API-Key header
- Rate limiting per client (in-memory, token bucket)
- Input sanitization for common injection patterns

Usage::

    from src.api.security import require_api_key, rate_limiter, sanitize_symbol
    app.add_middleware(rate_limiter)

    @app.get("/protected")
    async def protected(api_key: str = Depends(require_api_key)):
        ...
"""

from __future__ import annotations

import os
import re
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request, Depends
from fastapi.security import APIKeyHeader

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── API Key Authentication ───────────────────────────────────

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Allowed API keys (from environment). Comma-separated for multiple keys.
_VALID_KEYS: Optional[set] = None


def _get_valid_keys() -> set:
    """Load valid API keys from environment."""
    global _VALID_KEYS
    if _VALID_KEYS is None:
        raw = os.getenv("API_KEYS", "")
        if raw:
            _VALID_KEYS = {k.strip() for k in raw.split(",") if k.strip()}
        else:
            _VALID_KEYS = set()
    return _VALID_KEYS


def require_api_key(api_key: Optional[str] = Depends(_API_KEY_HEADER)) -> str:
    """
    Dependency that enforces API key authentication.

    If no API_KEYS env var is set, authentication is disabled (dev mode).
    """
    valid_keys = _get_valid_keys()

    # If no keys configured, skip auth (development mode)
    if not valid_keys:
        return "dev-mode"

    if not api_key or api_key not in valid_keys:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include X-API-Key header.",
        )
    return api_key


# ── Rate Limiting ────────────────────────────────────────────


class RateLimiter:
    """
    In-memory token bucket rate limiter.

    Tracks requests per client IP. Configurable via environment:
    - RATE_LIMIT_REQUESTS: Max requests per window (default: 100)
    - RATE_LIMIT_WINDOW_SECONDS: Window size (default: 60)
    """

    def __init__(self):
        self.requests: dict = defaultdict(list)
        self._max_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self._window = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    def check(self, client_id: str) -> bool:
        """Check if client is within rate limit. Returns True if allowed."""
        now = time.time()
        window_start = now - self._window

        # Clean old entries
        self.requests[client_id] = [
            t for t in self.requests[client_id] if t > window_start
        ]

        if len(self.requests[client_id]) >= self._max_requests:
            return False

        self.requests[client_id].append(now)
        return True

    def remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        now = time.time()
        window_start = now - self._window
        recent = [t for t in self.requests[client_id] if t > window_start]
        return max(0, self._max_requests - len(recent))


_rate_limiter = RateLimiter()


async def check_rate_limit(request: Request):
    """FastAPI dependency that enforces rate limiting."""
    client_ip = request.client.host if request.client else "unknown"

    if not _rate_limiter.check(client_ip):
        remaining = _rate_limiter.remaining(client_ip)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {_rate_limiter._window} seconds.",
            headers={
                "X-RateLimit-Remaining": str(remaining),
                "Retry-After": str(_rate_limiter._window),
            },
        )


# ── Input Sanitization ──────────────────────────────────────

# Patterns to reject
_DANGEROUS_PATTERNS = [
    re.compile(r"[;\-]{2}"),           # SQL comment
    re.compile(r"['\"]\s*(OR|AND)\s", re.I),  # SQL injection
    re.compile(r"<script", re.I),       # XSS
    re.compile(r"\{\{.*\}\}"),          # Template injection
    re.compile(r"__import__"),          # Python injection
    re.compile(r"\bexec\s*\("),         # Code execution
    re.compile(r"\beval\s*\("),         # Code evaluation
]


def sanitize_symbol(symbol: str) -> str:
    """
    Validate and sanitize a stock ticker symbol.

    Raises HTTPException if symbol looks malicious.
    """
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    # Strip whitespace and uppercase
    clean = symbol.strip().upper()

    # Ticker format: 1-10 alphanumeric chars, dots, and hyphens
    if not re.match(r"^[A-Z0-9.\-]{1,10}$", clean):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid symbol format: '{symbol}'. Expected 1-10 alphanumeric characters.",
        )

    return clean


def sanitize_input(text: str, field_name: str = "input", max_length: int = 1000) -> str:
    """
    Sanitize free-text input for injection patterns.

    Raises HTTPException if dangerous patterns detected.
    """
    if not text:
        return ""

    if len(text) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} exceeds maximum length of {max_length} characters.",
        )

    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(text):
            logger.warning(f"Rejected suspicious {field_name}: {text[:50]}...")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {field_name}: contains disallowed characters or patterns.",
            )

    return text.strip()
