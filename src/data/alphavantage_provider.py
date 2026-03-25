"""
Alpha Vantage Market Data Provider.

Implements ``MarketDataProvider`` using the Alpha Vantage API.
Free tier: 25 requests/day — sufficient for light development.
Premium key: up to 500 requests/day (and higher tiers available).

API docs: https://www.alphavantage.co/documentation/

Usage::

    from src.data.alphavantage_provider import AlphaVantageProvider
    provider = AlphaVantageProvider(api_key="YOUR_KEY")
    info = provider.get_info("AAPL")
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from src.data.provider import MarketDataProvider
from src.utils.logger import get_logger

logger = get_logger(__name__)

AV_BASE = "https://www.alphavantage.co/query"

# ── Period string → calendar days lookup ────────────────────────────────────

_PERIOD_DAYS: Dict[str, int] = {
    "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
    "6mo": 180, "1y": 365, "2y": 730, "5y": 1825,
    "10y": 3650, "max": 7300,
}


class AlphaVantageProvider(MarketDataProvider):
    """
    Concrete provider backed by Alpha Vantage.

    Requires an API key — free keys are available at
    https://www.alphavantage.co/support/#api-key

    All responses are mapped to the same dict key names and DataFrame column
    conventions used by ``YFinanceProvider`` so that tool modules can consume
    them without changes.
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError(
                "Alpha Vantage API key is required. "
                "Get a free key at https://www.alphavantage.co/support/#api-key"
            )
        self._api_key = api_key
        self._session = requests.Session()
        logger.info("AlphaVantageProvider initialized")

    # ── helpers ──────────────────────────────────────────────────────────────

    def _get(self, **params: Any) -> Optional[Dict]:
        """Issue a GET against the Alpha Vantage query endpoint."""
        params["apikey"] = self._api_key
        try:
            resp = self._session.get(AV_BASE, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            # AV returns an error message inside JSON on bad requests / rate limits
            if "Error Message" in data:
                logger.error(f"AV API error: {data['Error Message']}")
                return None
            if "Note" in data:
                logger.warning(f"AV API rate limit note: {data['Note']}")
                return None
            if "Information" in data:
                logger.warning(f"AV API info: {data['Information']}")
                return None
            return data
        except requests.RequestException as e:
            logger.error(f"AV request failed: {e}")
            return None

    @staticmethod
    def _empty_df() -> pd.DataFrame:
        return pd.DataFrame()

    @staticmethod
    def _empty_series() -> pd.Series:
        return pd.Series(dtype=float)

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """Convert a value to float, returning *default* on failure."""
        if value is None or value == "None" or value == "":
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    # ── Category 1: Info & Quote ────────────────────────────────────────────

    def get_info(self, symbol: str) -> Dict[str, Any]:
        symbol = symbol.upper().strip()
        data = self._get(function="OVERVIEW", symbol=symbol)
        if not data:
            return {}

        price = self._safe_float(data.get("AnalystTargetPrice"))
        eps = self._safe_float(data.get("EPS"))
        book_value = self._safe_float(data.get("BookValue"))
        dividend_per_share = self._safe_float(data.get("DividendPerShare"))
        shares = self._safe_float(data.get("SharesOutstanding"))

        # Attempt to get a current price from GLOBAL_QUOTE
        quote_data = self._get(function="GLOBAL_QUOTE", symbol=symbol)
        gq = (quote_data or {}).get("Global Quote", {})
        current_price = self._safe_float(gq.get("05. price"))
        prev_close = self._safe_float(gq.get("08. previous close"))
        volume = self._safe_float(gq.get("06. volume"))

        pe = self._safe_float(data.get("PERatio"))
        forward_pe = self._safe_float(data.get("ForwardPE"))

        return {
            "symbol": data.get("Symbol", symbol),
            "shortName": data.get("Name", ""),
            "longName": data.get("Name", ""),
            "sector": data.get("Sector", ""),
            "industry": data.get("Industry", ""),
            "country": data.get("Country", ""),
            "website": "",  # OVERVIEW does not provide website
            "longBusinessSummary": data.get("Description", ""),
            "marketCap": self._safe_float(data.get("MarketCapitalization")),
            "currentPrice": current_price or self._safe_float(data.get("50DayMovingAverage")),
            "regularMarketPrice": current_price or self._safe_float(data.get("50DayMovingAverage")),
            "previousClose": prev_close,
            "volume": volume,
            "regularMarketVolume": volume,
            "beta": self._safe_float(data.get("Beta")),
            "trailingPE": pe,
            "forwardPE": forward_pe,
            "dividendYield": (
                dividend_per_share / current_price
                if current_price and dividend_per_share
                else self._safe_float(data.get("DividendYield"))
            ),
            "trailingEps": eps,
            "bookValue": book_value,
            "priceToBook": self._safe_float(data.get("PriceToBookRatio")),
            "returnOnEquity": self._safe_float(data.get("ReturnOnEquityTTM")),
            "debtToEquity": 0,  # Not directly in OVERVIEW
            "totalRevenue": self._safe_float(data.get("RevenueTTM")),
            "netIncomeToCommon": self._safe_float(data.get("NetIncomeTTM")),  # AV sometimes has this
            "freeCashflow": 0,  # Not in OVERVIEW; available via CASH_FLOW
            "sharesOutstanding": shares,
            "exchange": data.get("Exchange", ""),
            "currency": data.get("Currency", "USD"),
            # AV-specific extras
            "_av_analyst_target": price,
            "_av_52wk_high": self._safe_float(data.get("52WeekHigh")),
            "_av_52wk_low": self._safe_float(data.get("52WeekLow")),
            "_av_profit_margin": self._safe_float(data.get("ProfitMargin")),
            "_av_operating_margin": self._safe_float(data.get("OperatingMarginTTM")),
            "_av_ev_to_ebitda": self._safe_float(data.get("EVToEBITDA")),
        }

    # ── Category 2: Historical Prices ───────────────────────────────────────

    def get_history(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        symbol = symbol.upper().strip()
        days = _PERIOD_DAYS.get(period, 365)
        cutoff = datetime.now() - timedelta(days=days)

        # Intraday intervals → TIME_SERIES_INTRADAY
        intraday_intervals = {"1m", "5m", "15m", "30m", "60m"}
        if interval in intraday_intervals:
            # Map shorthand to AV's expected format (e.g. "5m" → "5min")
            av_interval = interval.replace("m", "min")
            data = self._get(
                function="TIME_SERIES_INTRADAY",
                symbol=symbol,
                interval=av_interval,
                outputsize="full",
            )
            ts_key = f"Time Series ({av_interval})"
        else:
            # Daily data
            data = self._get(
                function="TIME_SERIES_DAILY",
                symbol=symbol,
                outputsize="full" if days > 100 else "compact",
            )
            ts_key = "Time Series (Daily)"

        if not data or ts_key not in data:
            return self._empty_df()

        ts = data[ts_key]
        rows = []
        for date_str, ohlcv in ts.items():
            dt = pd.to_datetime(date_str)
            if dt < pd.Timestamp(cutoff):
                continue
            rows.append({
                "Date": dt,
                "Open": self._safe_float(ohlcv.get("1. open")),
                "High": self._safe_float(ohlcv.get("2. high")),
                "Low": self._safe_float(ohlcv.get("3. low")),
                "Close": self._safe_float(ohlcv.get("4. close")),
                "Volume": self._safe_float(ohlcv.get("5. volume")),
            })

        if not rows:
            return self._empty_df()

        df = pd.DataFrame(rows).set_index("Date").sort_index()
        return df

    # ── Category 3: Financial Statements ────────────────────────────────────

    def _statement_to_df(
        self,
        function: str,
        symbol: str,
        report_key: str = "annualReports",
    ) -> pd.DataFrame:
        """Fetch a financial statement and transpose to yfinance layout.

        yfinance format: rows = metric names, columns = fiscal period dates
        (most recent first).
        """
        symbol = symbol.upper().strip()
        data = self._get(function=function, symbol=symbol)
        if not data or report_key not in data:
            return self._empty_df()

        reports = data[report_key]
        if not reports:
            return self._empty_df()

        df = pd.DataFrame(reports)
        if "fiscalDateEnding" in df.columns:
            df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
            df = df.set_index("fiscalDateEnding").sort_index(ascending=False)
        # Convert numeric columns
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.T  # Transpose: rows=metrics, cols=dates

    def get_income_statement(self, symbol: str) -> pd.DataFrame:
        return self._statement_to_df("INCOME_STATEMENT", symbol, "annualReports")

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        return self._statement_to_df("BALANCE_SHEET", symbol, "annualReports")

    def get_cash_flow(self, symbol: str) -> pd.DataFrame:
        return self._statement_to_df("CASH_FLOW", symbol, "annualReports")

    def get_quarterly_income_statement(self, symbol: str) -> pd.DataFrame:
        return self._statement_to_df("INCOME_STATEMENT", symbol, "quarterlyReports")

    def get_financials(
        self,
        symbol: str,
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

    # ── Category 4: Earnings ────────────────────────────────────────────────

    def get_earnings_history(self, symbol: str) -> pd.DataFrame:
        symbol = symbol.upper().strip()
        data = self._get(function="EARNINGS", symbol=symbol)
        if not data or "quarterlyEarnings" not in data:
            return self._empty_df()

        records = data["quarterlyEarnings"]
        if not records:
            return self._empty_df()

        df = pd.DataFrame(records)
        if "fiscalDateEnding" in df.columns:
            df["date"] = pd.to_datetime(df["fiscalDateEnding"])
            df = df.set_index("date").sort_index()

        # Rename to yfinance-compatible column names
        rename_map = {
            "reportedEPS": "epsActual",
            "estimatedEPS": "epsEstimate",
            "surprise": "epsDifference",
            "surprisePercentage": "surprisePct",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        # Convert numeric columns
        for col in ["epsActual", "epsEstimate", "epsDifference", "surprisePct"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def get_calendar(self, symbol: str) -> Any:
        """Alpha Vantage does not provide an earnings calendar endpoint.

        Returns ``None`` to signal that the data is unavailable.
        """
        logger.debug(
            f"AlphaVantageProvider.get_calendar({symbol}): "
            "not supported by Alpha Vantage API"
        )
        return None

    # ── Category 5: Dividends ───────────────────────────────────────────────

    def get_dividends(self, symbol: str) -> pd.Series:
        symbol = symbol.upper().strip()
        data = self._get(
            function="TIME_SERIES_MONTHLY_ADJUSTED",
            symbol=symbol,
        )
        ts_key = "Monthly Adjusted Time Series"
        if not data or ts_key not in data:
            return self._empty_series()

        ts = data[ts_key]
        records = []
        for date_str, vals in ts.items():
            div = self._safe_float(vals.get("7. dividend amount"))
            if div > 0:
                records.append({"date": pd.to_datetime(date_str), "dividend": div})

        if not records:
            return self._empty_series()

        df = pd.DataFrame(records).set_index("date").sort_index()
        return df["dividend"]

    # ── Category 6: Options (not supported) ─────────────────────────────────

    def get_options_expirations(self, symbol: str) -> List[str]:
        logger.debug(
            "AlphaVantageProvider: options data not available via Alpha Vantage"
        )
        return []

    def get_options_chain(
        self, symbol: str, expiration: str
    ) -> Dict[str, pd.DataFrame]:
        logger.debug(
            "AlphaVantageProvider: options chain not available via Alpha Vantage"
        )
        return {"calls": self._empty_df(), "puts": self._empty_df()}

    # ── Category 7: Holders & Insider Data (not supported) ──────────────────

    def get_insider_transactions(self, symbol: str) -> pd.DataFrame:
        logger.debug(
            "AlphaVantageProvider: insider transactions not available via Alpha Vantage"
        )
        return self._empty_df()

    def get_insider_purchases(self, symbol: str) -> pd.DataFrame:
        logger.debug(
            "AlphaVantageProvider: insider purchases not available via Alpha Vantage"
        )
        return self._empty_df()

    def get_institutional_holders(self, symbol: str) -> pd.DataFrame:
        logger.debug(
            "AlphaVantageProvider: institutional holders not available via Alpha Vantage"
        )
        return self._empty_df()

    def get_mutualfund_holders(self, symbol: str) -> pd.DataFrame:
        logger.debug(
            "AlphaVantageProvider: mutual fund holders not available via Alpha Vantage"
        )
        return self._empty_df()

    def get_major_holders(self, symbol: str) -> pd.DataFrame:
        logger.debug(
            "AlphaVantageProvider: major holders not available via Alpha Vantage"
        )
        return self._empty_df()

    # ── Category 8: News ────────────────────────────────────────────────────

    def get_news(self, symbol: str) -> List[Dict[str, Any]]:
        symbol = symbol.upper().strip()
        data = self._get(
            function="NEWS_SENTIMENT",
            tickers=symbol,
            limit="20",
        )
        if not data or "feed" not in data:
            return []

        articles: List[Dict[str, Any]] = []
        for item in data["feed"]:
            # AV timestamp format: "20230915T120000"
            raw_time = item.get("time_published", "")
            try:
                pub_dt = datetime.strptime(raw_time[:15], "%Y%m%dT%H%M%S")
                pub_ts = pub_dt.isoformat()
            except (ValueError, IndexError):
                pub_ts = raw_time

            articles.append({
                "title": item.get("title", ""),
                "publisher": item.get("source", ""),
                "link": item.get("url", ""),
                "providerPublishTime": pub_ts,
                "thumbnail": item.get("banner_image", ""),
                # AV-specific sentiment extras
                "_av_overall_sentiment": item.get("overall_sentiment_label", ""),
                "_av_overall_score": self._safe_float(
                    item.get("overall_sentiment_score")
                ),
            })

        return articles
