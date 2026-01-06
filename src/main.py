"""
Main entry point for the Financial Research Analyst Agent.
"""

import asyncio
from datetime import datetime

import uvicorn

from src.api.routes import app
from src.config import settings
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def run_api():
    """Run the FastAPI server."""
    logger.info("Starting Financial Research Analyst API...")
    logger.info(f"API docs available at: http://{settings.api.host}:{settings.api.port}/docs")
    
    uvicorn.run(
        "src.api.routes:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        log_level=settings.log_level.lower(),
    )


def demo_analysis():
    """Run a demonstration analysis."""
    from src.agents import FinancialResearchAgent
    
    logger.info("=" * 60)
    logger.info("Financial Research Analyst Agent - Demo")
    logger.info("=" * 60)
    
    # Initialize agent
    agent = FinancialResearchAgent()
    
    # Sample analysis
    symbol = "AAPL"
    logger.info(f"\nAnalyzing {symbol}...")
    
    try:
        result = agent.analyze(symbol)
        
        if result.get("success"):
            logger.info("\n✅ Analysis completed successfully!")
            logger.info(f"Symbol: {result.get('symbol')}")
            logger.info(f"Started: {result.get('started_at')}")
            logger.info(f"Completed: {result.get('completed_at')}")
        else:
            logger.error(f"❌ Analysis failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Demo error: {e}")
    
    logger.info("=" * 60)


def main():
    """Main entry point."""
    import sys
    
    setup_logging(
        log_level=settings.log_level,
        log_file=settings.log_file,
    )
    
    logger.info("=" * 60)
    logger.info("Financial Research Analyst Agent")
    logger.info(f"Version: 1.0.0")
    logger.info(f"Started at: {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "api":
            run_api()
        elif command == "demo":
            demo_analysis()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: api, demo")
            sys.exit(1)
    else:
        # Default: run API
        run_api()


if __name__ == "__main__":
    main()
