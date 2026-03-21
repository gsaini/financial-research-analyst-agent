"""
Insider & Institutional Activity Tracker (Feature 12).

Tracks insider transactions (Form 4 filings) and institutional holdings
from yfinance to generate a combined "smart money" signal.

Key capabilities:
- Parse insider buy/sell transactions over 30/60/90-day windows
- Detect cluster buying (multiple insiders buying in a short window)
- Track institutional ownership and top holders
- Generate a combined smart money score (0-100)

Usage
-----
>>> from src.tools.insider_activity import analyze_smart_money
>>> result = analyze_smart_money("AAPL")
>>> print(result["smart_money_signal"]["score"])
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from src.data import get_provider

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
# Insider Transactions
# ─────────────────────────────────────────────────────────────


def get_insider_activity(
    symbol: str,
    days: int = 90,
) -> Dict[str, Any]:
    """
    Fetch and parse insider transactions for a stock.

    Args:
        symbol: Stock ticker symbol.
        days: Look-back window in calendar days (default 90).

    Returns:
        Dict with parsed transactions, net activity, and cluster analysis.
    """
    try:
        provider = get_provider()

        # ── Insider transactions (Form 4 filings) ──
        txn_df = _safe_dataframe(provider.get_insider_transactions(symbol))
        purchases_df = _safe_dataframe(provider.get_insider_purchases(symbol))
        major = _safe_dataframe(provider.get_major_holders(symbol))

        # Parse insider ownership % from major_holders
        insider_ownership_pct = _extract_insider_ownership(major)

        # Parse individual transactions
        transactions = _parse_transactions(txn_df, days)

        # Compute net activity
        net_activity = _compute_net_activity(transactions)

        # Detect cluster buying
        cluster = _detect_cluster_buying(transactions)

        return {
            "transactions": transactions,
            "transaction_count": len(transactions),
            "net_activity": net_activity,
            "cluster_buying": cluster,
            "insider_ownership_pct": insider_ownership_pct,
        }

    except Exception as exc:
        logger.error(f"Failed to get insider activity for {symbol}: {exc}")
        return {
            "transactions": [],
            "transaction_count": 0,
            "net_activity": _empty_net(),
            "cluster_buying": {"detected": False, "details": "Data unavailable"},
            "insider_ownership_pct": None,
        }


def _safe_dataframe(obj) -> Optional[pd.DataFrame]:
    """Safely convert a yfinance attribute to a DataFrame (or None)."""
    if obj is None:
        return None
    if isinstance(obj, pd.DataFrame) and not obj.empty:
        return obj
    return None


def _extract_insider_ownership(major: Optional[pd.DataFrame]) -> Optional[float]:
    """Extract insider ownership % from major_holders."""
    if major is None:
        return None
    try:
        # major_holders typically has rows like:
        # 0  "xx.xx%"  "% of Shares Held by All Insider"
        for _, row in major.iterrows():
            label = str(row.iloc[-1]).lower() if len(row) > 1 else ""
            if "insider" in label:
                val_str = str(row.iloc[0]).replace("%", "").strip()
                return round(float(val_str), 2)
    except Exception:
        pass
    return None


def _parse_transactions(
    df: Optional[pd.DataFrame], days: int,
) -> List[Dict[str, Any]]:
    """Parse insider transactions into a clean list of dicts."""
    if df is None:
        return []

    results: List[Dict[str, Any]] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    for _, row in df.iterrows():
        try:
            # Date handling — yfinance may return various formats
            raw_date = row.get("Start Date", row.get("Date", row.get("startDate")))
            if raw_date is None:
                continue
            if isinstance(raw_date, str):
                txn_date = pd.to_datetime(raw_date, utc=True)
            elif hasattr(raw_date, "tzinfo"):
                txn_date = pd.Timestamp(raw_date)
                if txn_date.tzinfo is None:
                    txn_date = txn_date.tz_localize("UTC")
            else:
                txn_date = pd.Timestamp(raw_date, unit="s", tz="UTC")

            if txn_date < pd.Timestamp(cutoff):
                continue

            # Transaction fields
            insider = str(row.get("Insider", row.get("insider", "Unknown")))
            title = str(row.get("Position", row.get("position", row.get("Title", ""))))
            txn_text = str(row.get("Transaction", row.get("transaction", row.get("Text", ""))))
            shares = _to_float(row.get("Shares", row.get("shares", 0)))
            value = _to_float(row.get("Value", row.get("value", 0)))

            txn_type = _classify_transaction(txn_text, shares)

            results.append({
                "name": insider,
                "title": title,
                "transaction_type": txn_type,
                "shares": abs(int(shares)) if shares else 0,
                "value": round(abs(value), 2) if value else 0.0,
                "date": txn_date.strftime("%Y-%m-%d"),
            })
        except Exception:
            continue

    # Sort newest first
    results.sort(key=lambda t: t["date"], reverse=True)
    return results


def _classify_transaction(text: str, shares: float) -> str:
    """Classify a transaction as Buy, Sale, or Other."""
    text_lower = text.lower()
    if "purchase" in text_lower or "buy" in text_lower or "acquisition" in text_lower:
        return "Buy"
    if "sale" in text_lower or "sell" in text_lower or "disposition" in text_lower:
        return "Sale"
    # Fallback: negative shares → sale
    if shares and shares < 0:
        return "Sale"
    if shares and shares > 0:
        return "Buy"
    return "Other"


def _to_float(val) -> float:
    """Safely convert a value to float."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _compute_net_activity(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute net insider buy/sell activity."""
    if not transactions:
        return _empty_net()

    net_shares = 0
    net_value = 0.0
    buys = 0
    sales = 0

    for txn in transactions:
        if txn["transaction_type"] == "Buy":
            net_shares += txn["shares"]
            net_value += txn["value"]
            buys += 1
        elif txn["transaction_type"] == "Sale":
            net_shares -= txn["shares"]
            net_value -= txn["value"]
            sales += 1

    if net_value > 0:
        assessment = "Net buying (bullish signal)"
    elif net_value < 0 and buys > 0:
        assessment = "Mixed activity (some buying amid selling)"
    elif net_value < 0:
        assessment = "Net selling (may be planned dispositions)"
    else:
        assessment = "Neutral"

    return {
        "net_shares": net_shares,
        "net_value": round(net_value, 2),
        "total_buys": buys,
        "total_sales": sales,
        "assessment": assessment,
    }


def _empty_net() -> Dict[str, Any]:
    return {
        "net_shares": 0,
        "net_value": 0.0,
        "total_buys": 0,
        "total_sales": 0,
        "assessment": "No insider activity in period",
    }


def _detect_cluster_buying(
    transactions: List[Dict[str, Any]],
    window_days: int = 14,
    min_buyers: int = 2,
) -> Dict[str, Any]:
    """
    Detect cluster buying — multiple distinct insiders buying within
    a short window (one of the strongest bullish signals).
    """
    buys = [t for t in transactions if t["transaction_type"] == "Buy"]
    if len(buys) < min_buyers:
        return {"detected": False, "details": "Insufficient buy transactions"}

    # Group by 14-day windows
    dates = sorted(set(t["date"] for t in buys))
    if not dates:
        return {"detected": False, "details": "No buy dates found"}

    for anchor in dates:
        anchor_dt = datetime.strptime(anchor, "%Y-%m-%d")
        window_end = anchor_dt + timedelta(days=window_days)
        window_buys = [
            t for t in buys
            if anchor_dt <= datetime.strptime(t["date"], "%Y-%m-%d") <= window_end
        ]
        unique_buyers = set(t["name"] for t in window_buys)
        if len(unique_buyers) >= min_buyers:
            total_value = sum(t["value"] for t in window_buys)
            return {
                "detected": True,
                "buyers": list(unique_buyers),
                "buyer_count": len(unique_buyers),
                "window": f"{anchor} to {window_end.strftime('%Y-%m-%d')}",
                "total_value": round(total_value, 2),
                "details": (
                    f"{len(unique_buyers)} insiders bought within {window_days} days "
                    f"— strong bullish signal"
                ),
            }

    return {"detected": False, "details": "No cluster buying detected in any window"}


# ─────────────────────────────────────────────────────────────
# Institutional Holdings
# ─────────────────────────────────────────────────────────────


def get_institutional_holdings(symbol: str) -> Dict[str, Any]:
    """
    Fetch institutional and mutual fund holder information.

    Returns:
        Dict with top holders, ownership %, and summary.
    """
    try:
        provider = get_provider()

        inst_df = _safe_dataframe(provider.get_institutional_holders(symbol))
        mf_df = _safe_dataframe(provider.get_mutualfund_holders(symbol))
        major = _safe_dataframe(provider.get_major_holders(symbol))

        inst_pct = _extract_institutional_ownership(major)
        top_holders = _parse_holders(inst_df, label="institutional")
        top_funds = _parse_holders(mf_df, label="mutual_fund")

        return {
            "institutional_ownership_pct": inst_pct,
            "top_institutional_holders": top_holders,
            "top_mutual_fund_holders": top_funds,
            "total_institutional_holders": len(top_holders),
            "total_mutual_fund_holders": len(top_funds),
        }

    except Exception as exc:
        logger.error(f"Failed to get institutional holdings for {symbol}: {exc}")
        return {
            "institutional_ownership_pct": None,
            "top_institutional_holders": [],
            "top_mutual_fund_holders": [],
            "total_institutional_holders": 0,
            "total_mutual_fund_holders": 0,
        }


def _extract_institutional_ownership(major: Optional[pd.DataFrame]) -> Optional[float]:
    """Extract institutional ownership % from major_holders."""
    if major is None:
        return None
    try:
        for _, row in major.iterrows():
            label = str(row.iloc[-1]).lower() if len(row) > 1 else ""
            if "institution" in label and "insider" not in label:
                val_str = str(row.iloc[0]).replace("%", "").strip()
                return round(float(val_str), 2)
    except Exception:
        pass
    return None


def _parse_holders(
    df: Optional[pd.DataFrame], label: str = "institutional", max_rows: int = 10,
) -> List[Dict[str, Any]]:
    """Parse holder DataFrame into a list of dicts."""
    if df is None:
        return []

    holders: List[Dict[str, Any]] = []
    for i, (_, row) in enumerate(df.iterrows()):
        if i >= max_rows:
            break
        try:
            name = str(row.get("Holder", row.get("holder", f"Holder {i+1}")))
            shares = _to_float(row.get("Shares", row.get("shares", 0)))
            pct = _to_float(row.get("% Out", row.get("pctHeld", 0)))
            value = _to_float(row.get("Value", row.get("value", 0)))
            date_reported = row.get("Date Reported", row.get("dateReported", ""))
            if hasattr(date_reported, "strftime"):
                date_reported = date_reported.strftime("%Y-%m-%d")
            else:
                date_reported = str(date_reported) if date_reported else ""

            holders.append({
                "name": name,
                "shares": int(shares),
                "pct_held": round(pct * 100 if pct < 1 else pct, 2),
                "value": round(value, 2),
                "date_reported": date_reported,
            })
        except Exception:
            continue

    return holders


# ─────────────────────────────────────────────────────────────
# Smart Money Score
# ─────────────────────────────────────────────────────────────


def _compute_smart_money_score(
    insider: Dict[str, Any],
    institutional: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate a combined smart money score (0-100).

    Weights insider activity (buys weighted more than sales) and
    institutional ownership levels.
    """
    score = 50  # Neutral baseline

    # ── Insider component (±25 points) ──
    net = insider.get("net_activity", {})
    buys = net.get("total_buys", 0)
    sales = net.get("total_sales", 0)
    net_value = net.get("net_value", 0)

    # Buying is weighted 2x more than selling (selling can be for many reasons)
    if buys > 0:
        score += min(buys * 5, 15)  # up to +15 for buy count
    if net_value > 0:
        score += 10  # bonus for net positive dollar flow

    if sales > 0 and buys == 0:
        score -= min(sales * 3, 10)  # penalty if only selling
    if net_value < -5_000_000:
        score -= 5  # heavy net selling penalty

    # Cluster buying is the strongest signal
    cluster = insider.get("cluster_buying", {})
    if cluster.get("detected"):
        score += 10

    # ── Institutional component (±15 points) ──
    inst_pct = institutional.get("institutional_ownership_pct")
    if inst_pct is not None:
        if inst_pct > 70:
            score += 10  # high conviction from institutions
        elif inst_pct > 50:
            score += 5
        elif inst_pct < 20:
            score -= 5  # low institutional interest

    # Clamp
    score = max(0, min(100, score))

    # Assessment
    if score >= 75:
        assessment = "Strong bullish — significant insider buying and institutional conviction"
    elif score >= 60:
        assessment = "Moderately bullish — positive insider/institutional signals"
    elif score >= 40:
        assessment = "Neutral — no strong directional signal from smart money"
    elif score >= 25:
        assessment = "Moderately bearish — insider selling or low institutional interest"
    else:
        assessment = "Bearish — heavy insider selling with weak institutional support"

    return {
        "score": score,
        "assessment": assessment,
    }


# ─────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────


def analyze_smart_money(
    symbol: str,
    days: int = 90,
) -> Dict[str, Any]:
    """
    Comprehensive insider & institutional activity analysis.

    Args:
        symbol: Stock ticker symbol.
        days: Look-back window for insider transactions.

    Returns:
        Dict with insider_activity, institutional_activity,
        smart_money_signal, and metadata.
    """
    start = datetime.now(timezone.utc)

    insider = get_insider_activity(symbol, days=days)
    institutional = get_institutional_holdings(symbol)
    smart_money = _compute_smart_money_score(insider, institutional)

    exec_time = (datetime.now(timezone.utc) - start).total_seconds()

    return {
        "symbol": symbol,
        "period_days": days,
        "insider_activity": insider,
        "institutional_activity": institutional,
        "smart_money_signal": smart_money,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "execution_time_seconds": round(exec_time, 3),
    }
