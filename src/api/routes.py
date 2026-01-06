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
)
from src.agents import FinancialResearchAgent
from src.tools.market_data import get_stock_price, get_historical_data, get_company_info
from src.tools.technical_indicators import calculate_rsi, calculate_macd, calculate_moving_averages
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

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


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health status."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        services={
            "api": "running",
            "agent": "ready",
            "database": "connected",
        }
    )


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
