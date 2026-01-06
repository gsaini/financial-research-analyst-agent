"""
Command Line Interface for the Financial Research Analyst Agent.
"""

import argparse
import json
import sys
from datetime import datetime

from src.agents import FinancialResearchAgent
from src.tools.market_data import get_stock_price, get_historical_data, get_company_info
from src.tools.technical_indicators import calculate_rsi, calculate_macd, calculate_moving_averages
from src.utils.logger import get_logger

logger = get_logger(__name__)


def analyze_command(args):
    """Handle the analyze command."""
    symbol = args.symbol.upper()
    print(f"\n📊 Analyzing {symbol}...")
    print("=" * 60)
    
    # Get price data
    price_data = get_stock_price(symbol)
    
    if "error" in price_data:
        print(f"❌ Error: {price_data['error']}")
        return
    
    print(f"\n💰 Current Price: ${price_data.get('current_price', 0):.2f}")
    print(f"📈 Change: {price_data.get('change_percent', 0):.2f}%")
    print(f"📊 Volume: {price_data.get('volume', 0):,}")
    print(f"💎 Market Cap: ${price_data.get('market_cap', 0):,.0f}")
    
    # Technical Analysis
    print("\n" + "=" * 60)
    print("📈 TECHNICAL ANALYSIS")
    print("=" * 60)
    
    hist_data = get_historical_data(symbol, period="1y")
    if "closes" in hist_data and len(hist_data["closes"]) > 0:
        closes = hist_data["closes"]
        
        rsi = calculate_rsi(closes)
        print(f"\nRSI (14): {rsi.get('value', 'N/A')}")
        print(f"Signal: {rsi.get('signal', 'N/A')}")
        
        macd = calculate_macd(closes)
        print(f"\nMACD: {macd.get('macd_line', 'N/A')}")
        print(f"Signal Line: {macd.get('signal_line', 'N/A')}")
        print(f"Trend: {macd.get('trend', 'N/A')}")
        
        ma = calculate_moving_averages(closes)
        print(f"\nSMA 20: ${ma.get('sma_20', 0):.2f}")
        print(f"SMA 50: ${ma.get('sma_50', 0):.2f}")
        print(f"SMA 200: ${ma.get('sma_200', 0):.2f}")
        if "trend" in ma:
            print(f"MA Trend: {ma['trend'].upper()}")
    
    # Company Info
    if args.verbose:
        print("\n" + "=" * 60)
        print("🏢 COMPANY INFORMATION")
        print("=" * 60)
        
        company = get_company_info(symbol)
        print(f"\nName: {company.get('name', 'N/A')}")
        print(f"Sector: {company.get('sector', 'N/A')}")
        print(f"Industry: {company.get('industry', 'N/A')}")
        if company.get('description'):
            print(f"\nDescription: {company['description'][:200]}...")
    
    # Recommendation
    print("\n" + "=" * 60)
    print("💡 RECOMMENDATION")
    print("=" * 60)
    
    rsi_value = rsi.get('value', 50) if 'rsi' in dir() else 50
    macd_hist = macd.get('histogram', 0) if 'macd' in dir() else 0
    
    if rsi_value < 30 and macd_hist > 0:
        recommendation = "BUY"
        confidence = 75
    elif rsi_value > 70 and macd_hist < 0:
        recommendation = "SELL"
        confidence = 75
    else:
        recommendation = "HOLD"
        confidence = 50
    
    print(f"\nAction: {recommendation}")
    print(f"Confidence: {confidence}%")
    print(f"\nAnalysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")


def portfolio_command(args):
    """Handle the portfolio command."""
    symbols = [s.upper() for s in args.symbols]
    
    print(f"\n📊 Analyzing Portfolio: {', '.join(symbols)}")
    print("=" * 60)
    
    results = []
    for symbol in symbols:
        price_data = get_stock_price(symbol)
        if "error" not in price_data:
            results.append({
                "symbol": symbol,
                "price": price_data.get("current_price", 0),
                "change": price_data.get("change_percent", 0),
            })
            print(f"\n{symbol}: ${price_data.get('current_price', 0):.2f} ({price_data.get('change_percent', 0):+.2f}%)")
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to {args.output}")
    
    print("=" * 60 + "\n")


def dashboard_command(args):
    """Handle the dashboard command."""
    print(f"\n🌐 Starting Web Dashboard on port {args.port}...")
    print("=" * 60)
    
    import uvicorn
    from src.api.routes import app
    
    uvicorn.run(app, host="0.0.0.0", port=args.port)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="financial-analyst",
        description="Financial Research Analyst Agent CLI",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a stock symbol")
    analyze_parser.add_argument("symbol", type=str, help="Stock ticker symbol")
    analyze_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    analyze_parser.set_defaults(func=analyze_command)
    
    # Portfolio command
    portfolio_parser = subparsers.add_parser("portfolio", help="Analyze portfolio")
    portfolio_parser.add_argument("symbols", nargs="+", help="Stock symbols")
    portfolio_parser.add_argument("-o", "--output", type=str, help="Output file")
    portfolio_parser.set_defaults(func=portfolio_command)
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Start web dashboard")
    dashboard_parser.add_argument("-p", "--port", type=int, default=8080, help="Port number")
    dashboard_parser.set_defaults(func=dashboard_command)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
