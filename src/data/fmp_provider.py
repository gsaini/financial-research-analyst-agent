"""
Financial Modeling Prep (FMP) Provider.

Implements ``MarketDataProvider`` using the FMP API.
Free tier: 250 requests/day — sufficient for development.

API docs: https://site.financialmodelingprep.com/developer/docs

Usage::

    from src.data.provider import get_provider
    provider = get_provider("fmp")  # requires FMP_API_KEY in .env
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from src.data.provider import MarketDataProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)

FMP_BASE = "https://financialmodelingprep.com/api/v3"


class FMPProvider(MarketDataProvider):
    """
    Concrete provider backed by Financial Modeling Prep.

    Requires an API key (free tier available at https://site.financialmodelingprep.com).
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError(
                "FMP API key is required. Get a free key at "
                "https://site.financialmodelingprep.com/register"
            )
        self._api_key = api_key
        self._session = requests.Session()
        logger.info("FMPProvider initialized")

    # ── helpers ──────────────────────────────────────────────────

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make a GET request to FMP API."""
        params = params or {}
        params["apikey"] = self._api_key
        url = f"{FMP_BASE}/{endpoint}"
        try:
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"FMP API error ({endpoint}): {e}")
            return None

    @staticmethod
    def _empty_df() -> pd.DataFrame:
        return pd.DataFrame()

    @staticmethod
    def _empty_series() -> pd.Series:
        return pd.Series(dtype=float)

    # ── Category 1: Info & Quote ─────────────────────────────────

    def get_info(self, symbol: str) -> Dict[str, Any]:
        symbol = symbol.upper().strip()
        profile = self._get(f"profile/{symbol}")
        if not profile:
            return {}
        p = profile[0] if isinstance(profile, list) else profile

        # Map FMP fields to the yfinance-compatible structure tools expect
        return {
            "symbol": p.get("symbol", symbol),
            "shortName": p.get("companyName", ""),
            "longName": p.get("companyName", ""),
            "sector": p.get("sector", ""),
            "industry": p.get("industry", ""),
            "country": p.get("country", ""),
            "website": p.get("website", ""),
            "longBusinessSummary": p.get("description", ""),
            "marketCap": p.get("mktCap", 0),
            "currentPrice": p.get("price", 0),
            "regularMarketPrice": p.get("price", 0),
            "previousClose": p.get("previousClose", 0) or p.get("price", 0),
            "volume": p.get("volAvg", 0),
            "regularMarketVolume": p.get("volAvg", 0),
            "beta": p.get("beta", 0),
            "trailingPE": p.get("peRatio") or p.get("pe", 0),
            "forwardPE": p.get("peRatio", 0),
            "dividendYield": (p.get("lastDiv", 0) or 0) / max(p.get("price", 1), 1),
            "trailingEps": p.get("eps", 0),
            "bookValue": p.get("bookValuePerShare", 0),
            "priceToBook": p.get("pbRatio", 0),
            "returnOnEquity": p.get("roe", 0),
            "debtToEquity": p.get("debtToEquity", 0),
            "totalRevenue": p.get("revenue", 0),
            "netIncomeToCommon": p.get("netIncome", 0),
            "freeCashflow": p.get("freeCashFlow", 0),
            "sharesOutstanding": p.get("sharesOutstanding", 0),
            "exchange": p.get("exchange", ""),
            "currency": p.get("currency", "USD"),
            # FMP-specific extras
            "_fmp_ceo": p.get("ceo", ""),
            "_fmp_ipo_date": p.get("ipoDate", ""),
            "_fmp_full_time_employees": p.get("fullTimeEmployees", 0),
        }

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        symbol = symbol.upper().strip()
        data = self._get(f"quote/{symbol}")
        if not data:
            return super().get_quote(symbol)
        q = data[0] if isinstance(data, list) else data
        return {
            "symbol": symbol,
            "price": q.get("price", 0),
            "previous_close": q.get("previousClose", 0),
            "change": q.get("change", 0),
            "change_pct": q.get("changesPercentage", 0),
            "volume": q.get("volume", 0),
        }

    # ── Category 2: Historical Prices ────────────────────────────

    def get_history(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        symbol = symbol.upper().strip()

        # Convert period string to date range
        period_map = {
            "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
            "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "10y": 3650,
            "max": 7300,
        }
        days = period_map.get(period, 365)
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")

        data = self._get(
            f"historical-price-full/{symbol}",
            params={"from": from_date, "to": to_date},
        )
        if not data or "historical" not in data:
            return self._empty_df()

        df = pd.DataFrame(data["historical"])
        if df.empty:
            return self._empty_df()

        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()

        # Rename to match yfinance convention (capitalized)
        rename = {
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "adjClose": "Adj Close", "volume": "Volume",
        }
        df = df.rename(columns=rename)
        return df[["Open", "High", "Low", "Close", "Volume"]]

    # ── Category 3: Financial Statements ─────────────────────────

    def _fetch_statement(self, endpoint: str, symbol: str) -> pd.DataFrame:
        """Fetch a financial statement and return as a DataFrame."""
        symbol = symbol.upper().strip()
        data = self._get(f"{endpoint}/{symbol}", params={"limit": 5})
        if not data:
            return self._empty_df()
        df = pd.DataFrame(data)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index(ascending=False)
        return df.T  # Transpose to match yfinance format (rows=metrics, cols=dates)

    def get_income_statement(self, symbol: str) -> pd.DataFrame:
        return self._fetch_statement("income-statement", symbol)

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        return self._fetch_statement("balance-sheet-statement", symbol)

    def get_cash_flow(self, symbol: str) -> pd.DataFrame:
        return self._fetch_statement("cash-flow-statement", symbol)

    def get_quarterly_income_statement(self, symbol: str) -> pd.DataFrame:
        symbol = symbol.upper().strip()
        data = self._get(
            f"income-statement/{symbol}",
            params={"period": "quarter", "limit": 8},
        )
        if not data:
            return self._empty_df()
        df = pd.DataFrame(data)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index(ascending=False)
        return df.T

    def get_financials(
        self, symbol: str,
        statement_type: str = "income_statement",
        freq: str = "yearly",
    ) -> pd.DataFrame:
        if freq == "yearly":
            if statement_type == "income_statement":
                return self.get_income_statement(symbol)
            elif statement_type == "balance_sheet":
                return self.get_balance_sheet(symbol)
            elif statement_type == "cash_flow":
                return self.get_cash_flow(symbol)
        elif freq == "quarterly":
            if statement_type == "income_statement":
                return self.get_quarterly_income_statement(symbol)
        return self._empty_df()

    # ── Category 4: Earnings ─────────────────────────────────────

    def get_earnings_history(self, symbol: str) -> pd.DataFrame:
        symbol = symbol.upper().strip()
        data = self._get(f"historical/earning_calendar/{symbol}", params={"limit": 20})
        if not data:
            return self._empty_df()
        df = pd.DataFrame(data)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
        # Rename to match yfinance-like columns
        rename = {
            "epsEstimated": "epsEstimate",
            "epsActual": "epsActual",
            "revenueEstimated": "revenueEstimate",
            "revenue": "revenue",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
        return df

    def get_calendar(self, symbol: str) -> Any:
        symbol = symbol.upper().strip()
        data = self._get(f"earning_calendar", params={"symbol": symbol})
        if not data:
            return None
        # Return the next upcoming earnings date
        upcoming = [d for d in data if d.get("date", "") >= datetime.now().strftime("%Y-%m-%d")]
        if upcoming:
            return {"earningsDate": upcoming[0].get("date")}
        return data[0] if data else None

    # ── Category 5: Dividends ────────────────────────────────────

    def get_dividends(self, symbol: str) -> pd.Series:
        symbol = symbol.upper().strip()
        data = self._get(f"historical-price-full/stock_dividend/{symbol}")
        if not data or "historical" not in data:
            return self._empty_series()
        df = pd.DataFrame(data["historical"])
        if df.empty:
            return self._empty_series()
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["dividend"].sort_index()

    # ── Category 6: Options ──────────────────────────────────────

    def get_options_expirations(self, symbol: str) -> List[str]:
        # FMP free tier doesn't include options data
        logger.warning("FMP free tier does not support options data")
        return []

    def get_options_chain(self, symbol: str, expiration: str) -> Dict[str, pd.DataFrame]:
        logger.warning("FMP free tier does not support options data")
        return {"calls": self._empty_df(), "puts": self._empty_df()}

    # ── Category 7: Holders & Insider Data ───────────────────────

    def get_insider_transactions(self, symbol: str) -> pd.DataFrame:
        symbol = symbol.upper().strip()
        data = self._get(f"insider-trading", params={"symbol": symbol, "limit": 50})
        if not data:
            return self._empty_df()
        return pd.DataFrame(data)

    def get_insider_purchases(self, symbol: str) -> pd.DataFrame:
        df = self.get_insider_transactions(symbol)
        if df.empty:
            return self._empty_df()
        buys = df[df.get("transactionType", pd.Series(dtype=str)).str.contains("Purchase|Buy", case=False, na=False)]
        return buys if not buys.empty else self._empty_df()

    def get_institutional_holders(self, symbol: str) -> pd.DataFrame:
        symbol = symbol.upper().strip()
        data = self._get(f"institutional-holder/{symbol}")
        if not data:
            return self._empty_df()
        return pd.DataFrame(data)

    def get_mutualfund_holders(self, symbol: str) -> pd.DataFrame:
        symbol = symbol.upper().strip()
        data = self._get(f"mutual-fund-holder/{symbol}")
        if not data:
            return self._empty_df()
        return pd.DataFrame(data)

    def get_major_holders(self, symbol: str) -> pd.DataFrame:
        # FMP doesn't have a direct equivalent; synthesize from institutional data
        inst = self.get_institutional_holders(symbol)
        if inst.empty:
            return self._empty_df()
        total_shares = inst["shares"].sum() if "shares" in inst.columns else 0
        return pd.DataFrame({
            "Value": [f"{len(inst)} institutions", f"{total_shares:,.0f} shares"],
            "Metric": ["Institutional Holders", "Institutional Shares"],
        })

    # ── Category 8: News ─────────────────────────────────────────

    def get_news(self, symbol: str) -> List[Dict[str, Any]]:
        symbol = symbol.upper().strip()
        data = self._get(f"stock_news", params={"tickers": symbol, "limit": 20})
        if not data:
            return []
        # Normalize to yfinance-compatible format
        return [
            {
                "title": item.get("title", ""),
                "publisher": item.get("site", ""),
                "link": item.get("url", ""),
                "providerPublishTime": item.get("publishedDate", ""),
                "thumbnail": item.get("image", ""),
            }
            for item in data
        ]
