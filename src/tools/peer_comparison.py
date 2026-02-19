"""
Peer Comparison Tool for Financial Research Analyst.

This module is responsible for discovering peer companies based on sector, industry,
and market cap, and performing comparative analysis on key financial metrics.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio
import concurrent.futures
import yfinance as yf
import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)

# ─── DEFAULT UNIVERSE FOR PEER DISCOVERY ──────────────────────────────────────
# In a production system, this would be a database or larger file.
# We include a representative list of ~100 major US stocks across sectors.

DEFAULT_UNIVERSE = [
    # Technology
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "ORCL", "CRM", "AMD", "ADBE", "CSCO", "INTC", "IBM", "QCOM", "TXN", "NOW", "INTU", "UBER", "ABNB", "PANW", "SNOW", "PLTR",
    # Financials
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "AXP", "V", "MA", "PYPL", "COIN", "SCHW", "MMC", "CB", "PGR",
    # Healthcare
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "AVGO", "DHR", "ABT", "PFE", "AMGN", "ISRG", "SYK", "GILD", "VRTX", "REGN", "CVS", "CI",
    # Consumer Discretionary
    "HD", "MCD", "NKE", "SBUX", "LOW", "BKNG", "TJX", "TGT", "LULU", "CMG", "MAR", "HLT",
    # Consumer Staples
    "WMT", "PG", "COST", "KO", "PEP", "PM", "EL", "CL", "KMB", "GIS", "MO",
    # Industrials
    "CAT", "DE", "HON", "UNP", "UPS", "GE", "BA", "LMT", "RTX", "ADP", "MMM", "ETN",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HES",
    # Communication Services
    "NFLX", "DIS", "CMCSA", "TMUS", "VZ", "T", "CHTR",
    # Utilities
    "NEE", "DUK", "SO", "AEP", "SRE", "D",
    # Real Estate
    "PLD", "AMT", "EQIX", "CCI", "PSA", "O",
    # Materials
    "LIN", "SHW", "FCX", "APD", "NEM", "CTVA"
]

# Cache for peer discovery results to avoid re-scanning
_PEER_CACHE: Dict[str, List[str]] = {}


def _fetch_info_cached(symbol: str) -> Dict[str, Any]:
    """Helper to fetch info with error handling."""
    try:
        return yf.Ticker(symbol).info
    except Exception:
        return {}


async def discover_peers(symbol: str, limit: int = 5) -> Dict[str, Any]:
    """
    Find relevant peer companies for a given stock symbol.

    Criteria for peers:
    1. Same Sector
    2. Same Industry (preferred)
    3. Market Cap within 0.25x - 4x of target (to compare apples-to-apples)

    Args:
        symbol: Target stock ticker.
        limit: Max number of peers to return.

    Returns:
        Dict containing target info and list of peer symbols.
    """
    if symbol in _PEER_CACHE:
        logger.info(f"Using cached peers for {symbol}")
        # We need to re-fetch target info though to return it
        info = _fetch_info_cached(symbol)
        return {
            "symbol": symbol,
            "target_sector": info.get("sector"),
            "target_industry": info.get("industry"),
            "target_mcap": info.get("marketCap", 0),
            "peers": _PEER_CACHE[symbol][:limit],
            "peer_count": len(_PEER_CACHE[symbol])
        }

    try:
        # Get target info
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _fetch_info_cached, symbol)
        
        target_sector = info.get("sector")
        target_industry = info.get("industry")
        target_mcap = info.get("marketCap", 0)

        if not target_sector:
            logger.warning(f"No sector info found for {symbol}")
            return {"symbol": symbol, "error": "Sector info unavailable"}

        # Build candidate list
        candidates = set(DEFAULT_UNIVERSE)
        try:
            from src.tools.theme_mapper import list_available_themes
            themes = list_available_themes()
            for t in themes:
                candidates.update(t.get("constituents", []))
        except ImportError:
            pass

        if symbol in candidates:
            candidates.remove(symbol)
            
        all_candidates = list(candidates)
        matches = []
        
        # Parallel fetch of candidate info
        # We limit concurrency to 10 to be polite to the API
        semaphore = asyncio.Semaphore(10)

        async def check_candidate(cand_sym):
            async with semaphore:
                try:
                    c_info = await loop.run_in_executor(None, _fetch_info_cached, cand_sym)
                    if not c_info:
                        return None
                        
                    c_sector = c_info.get("sector")
                    c_industry = c_info.get("industry")
                    c_mcap = c_info.get("marketCap", 0)
                    
                    score = 0
                    if c_sector == target_sector:
                        score += 5
                    if c_industry == target_industry:
                        score += 10
                    
                    if target_mcap > 0 and c_mcap > 0:
                        ratio = c_mcap / target_mcap
                        if 0.25 <= ratio <= 4.0:
                            score += 5
                        elif 0.1 <= ratio <= 10.0:
                            score += 2
                            
                    if score >= 5:
                        return {
                            "symbol": cand_sym,
                            "score": score,
                            "market_cap": c_mcap,
                            "sector": c_sector,
                            "industry": c_industry
                        }
                except Exception:
                    pass
            return None

        # Execute parallel checks
        tasks = [check_candidate(s) for s in all_candidates]
        results = await asyncio.gather(*tasks)
        
        # Filter None results
        matches = [r for r in results if r is not None]
        
        # Sort by score (desc), then by market cap proximity
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        top_peers = [m["symbol"] for m in matches[:limit]]
        
        # Update cache
        if top_peers:
            _PEER_CACHE[symbol] = top_peers
        
        return {
            "symbol": symbol,
            "target_sector": target_sector,
            "target_industry": target_industry,
            "target_mcap": target_mcap,
            "peers": top_peers,
            "peer_count": len(top_peers)
        }
        
    except Exception as e:
        logger.error(f"Error discovering peers for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


async def compare_peers(symbol: str, peer_symbols: List[str] = None) -> Dict[str, Any]:
    """
    Compare target stock with its peers across multiple metrics.

    Args:
        symbol: Target stock ticker.
        peer_symbols: Optional list of peers (if None, auto-discovers).

    Returns:
        Comprehensive comparison dictionary.
    """
    try:
        if not peer_symbols:
            discovery = await discover_peers(symbol)
            if "error" in discovery:
                return discovery
            peer_symbols = discovery.get("peers", [])
        
        if not peer_symbols:
            return {
                "symbol": symbol,
                "error": "No peers found for comparison"
            }
        
        all_symbols = [symbol] + peer_symbols
        comparison_data = {}
        
        # Parallel fetch for comparison data
        loop = asyncio.get_event_loop()
        
        async def fetch_metrics(sym):
            try:
                info = await loop.run_in_executor(None, _fetch_info_cached, sym)
                if not info:
                    return None
                    
                return {
                    "symbol": sym,
                    "metrics": {
                        "price": info.get("currentPrice", 0),
                        "market_cap": info.get("marketCap", 0),
                        "pe_ratio": info.get("trailingPE"),
                        "forward_pe": info.get("forwardPE"),
                        "peg_ratio": info.get("pegRatio"),
                        "pb_ratio": info.get("priceToBook"),
                        "ps_ratio": info.get("priceToSalesTrailing12Months"),
                        "ev_ebitda": info.get("enterpriseToEbitda"),
                        "debt_to_equity": info.get("debtToEquity"),
                        "profit_margin": info.get("profitMargins"),
                        "operating_margin": info.get("operatingMargins"),
                        "revenue_growth": info.get("revenueGrowth"),
                        "earnings_growth": info.get("earningsGrowth"),
                        "roe": info.get("returnOnEquity"),
                        "roa": info.get("returnOnAssets"),
                        "dividend_yield": info.get("dividendYield"),
                        "beta": info.get("beta"),
                        "sector": info.get("sector", "N/A"),
                        "industry": info.get("industry", "N/A")
                    }
                }
            except Exception as e:
                logger.warning(f"Failed to fetch data for {sym}: {e}")
                return None

        tasks = [fetch_metrics(s) for s in all_symbols]
        results = await asyncio.gather(*tasks)
        
        # Process results
        for res in results:
            if res:
                comparison_data[res["symbol"]] = res["metrics"]
        
        valid_symbols = list(comparison_data.keys())
        if symbol not in valid_symbols:
            return {"error": "Failed to fetch data for target symbol"}
            
        target_metrics = comparison_data[symbol]
        peer_metrics = {s: d for s, d in comparison_data.items() if s != symbol}
        
        # Compute aggregates and rankings
        aggregates = {}
        metric_keys = [
            "pe_ratio", "forward_pe", "peg_ratio", "pb_ratio", "ps_ratio", "ev_ebitda",
            "debt_to_equity", "profit_margin", "operating_margin", 
            "revenue_growth", "earnings_growth", "roe", "roa", 
            "dividend_yield", "beta"
        ]
        
        rankings = {}
        rel_valuation = {}
        strengths = []
        weaknesses = []
        
        for key in metric_keys:
            # Filter None values
            values = []
            for s in valid_symbols:
                val = comparison_data[s].get(key)
                if val is not None:
                    values.append(val)
            
            if not values:
                continue
                
            median_val = float(np.median(values))
            mean_val = float(np.mean(values))
            
            aggregates[key] = {
                "median": median_val,
                "mean": mean_val,
                "min": float(min(values)),
                "max": float(max(values))
            }
            
            # Ranking and Assessment
            target_val = target_metrics.get(key)
            if target_val is not None:
                # Determine sort order (usually higher is better, except for valuation ratios)
                lower_is_better = key in ["pe_ratio", "forward_pe", "peg_ratio", "pb_ratio", "ps_ratio", "ev_ebitda", "debt_to_equity", "beta"]
                
                sorted_vals = sorted(values)
                rank = sorted_vals.index(target_val) + 1
                total = len(values)
                
                percentile = (rank / total) * 100
                if lower_is_better:
                    # For P/E, 10th percentile is "better" (cheaper) than 90th
                    rankings[key] = f"{int(percentile)}th percentile (Lower is generally cheaper/safer)"
                else:
                    rankings[key] = f"{int(percentile)}th percentile"
                
                # Deviation from median
                if median_val != 0:
                    diff_pct = ((target_val - median_val) / abs(median_val)) * 100
                    status = "Premium" if diff_pct > 0 else "Discount"
                    rel_valuation[key] = f"{status} of {abs(round(diff_pct, 1))}% vs Median"
                    
                    # Generate strength/weakness text
                    if key == "roe" and diff_pct > 20:
                        strengths.append(f"Strong ROE ({round(target_val*100, 1)}% vs median {round(median_val*100, 1)}%)")
                    elif key == "profit_margin" and diff_pct > 20:
                        strengths.append(f"High profit margins ({round(target_val*100, 1)}% vs median {round(median_val*100, 1)}%)")
                    elif key == "revenue_growth" and diff_pct > 20:
                        strengths.append(f"Superior revenue growth ({round(target_val*100, 1)}% vs median {round(median_val*100, 1)}%)")
                    elif key == "pe_ratio" and diff_pct < -20:
                        strengths.append(f"Discounted valuation (P/E {round(target_val, 1)} vs median {round(median_val, 1)})")
                    elif key == "debt_to_equity" and diff_pct < -20:
                        strengths.append(f"Strong balance sheet (Lower debt/equity than peers)")
                        
                    if key == "roe" and diff_pct < -20:
                        weaknesses.append(f"Weak ROE ({round(target_val*100, 1)}% vs median {round(median_val*100, 1)}%)")
                    elif key == "profit_margin" and diff_pct < -20:
                        weaknesses.append(f"Low profit margins ({round(target_val*100, 1)}% vs median {round(median_val*100, 1)}%)")
                    elif key == "pe_ratio" and diff_pct > 30:
                        weaknesses.append(f"High valuation (P/E {round(target_val, 1)} vs median {round(median_val, 1)})")

        return {
            "target": symbol,
            "peer_group": list(peer_metrics.keys()),
            "metrics": comparison_data,
            "peer_aggregates": aggregates,
            "percentile_rankings": rankings,
            "relative_valuation": rel_valuation,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error comparing peers for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}
