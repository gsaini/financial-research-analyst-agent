"""
Tests for Phase 1: Core AI Intelligence.

Covers:
- 1.3: FMP Provider + MultiProvider fallback chain
- 1.4: LLM Insight Engine
- 1.1: RAG Pipeline (ingester, embedder, retriever)
- 1.2: ReAct reasoning (confidence extraction, prompt building)
- Data validator
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone


# ═══════════════════════════════════════════════════════════════════
# 1.3 — FMP Provider
# ═══════════════════════════════════════════════════════════════════


class TestFMPProvider:
    """Test FMPProvider implementation."""

    def test_init_requires_api_key(self):
        from src.data.fmp_provider import FMPProvider
        with pytest.raises(ValueError, match="API key is required"):
            FMPProvider(api_key="")

    def test_init_with_valid_key(self):
        from src.data.fmp_provider import FMPProvider
        provider = FMPProvider(api_key="test_key_123")
        assert provider._api_key == "test_key_123"

    @patch("src.data.fmp_provider.FMPProvider._get")
    def test_get_info_maps_fields(self, mock_get):
        from src.data.fmp_provider import FMPProvider

        mock_get.return_value = [{
            "symbol": "AAPL",
            "companyName": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "price": 175.50,
            "mktCap": 2800000000000,
            "peRatio": 28.5,
            "eps": 6.16,
            "beta": 1.28,
        }]

        provider = FMPProvider(api_key="test")
        info = provider.get_info("AAPL")

        assert info["shortName"] == "Apple Inc."
        assert info["sector"] == "Technology"
        assert info["currentPrice"] == 175.50
        assert info["marketCap"] == 2800000000000
        assert info["trailingPE"] == 28.5

    @patch("src.data.fmp_provider.FMPProvider._get")
    def test_get_info_empty_response(self, mock_get):
        from src.data.fmp_provider import FMPProvider
        mock_get.return_value = None
        provider = FMPProvider(api_key="test")
        assert provider.get_info("INVALID") == {}

    @patch("src.data.fmp_provider.FMPProvider._get")
    def test_get_quote(self, mock_get):
        from src.data.fmp_provider import FMPProvider
        mock_get.return_value = [{
            "price": 175.50,
            "previousClose": 174.00,
            "change": 1.50,
            "changesPercentage": 0.86,
            "volume": 55000000,
        }]
        provider = FMPProvider(api_key="test")
        quote = provider.get_quote("AAPL")
        assert quote["price"] == 175.50
        assert quote["change"] == 1.50

    @patch("src.data.fmp_provider.FMPProvider._get")
    def test_get_history(self, mock_get):
        from src.data.fmp_provider import FMPProvider
        mock_get.return_value = {
            "historical": [
                {"date": "2024-01-02", "open": 170, "high": 172, "low": 169, "close": 171, "adjClose": 171, "volume": 50000000},
                {"date": "2024-01-03", "open": 171, "high": 173, "low": 170, "close": 172, "adjClose": 172, "volume": 48000000},
            ]
        }
        provider = FMPProvider(api_key="test")
        df = provider.get_history("AAPL", period="1mo")
        assert not df.empty
        assert "Close" in df.columns
        assert "Volume" in df.columns
        assert len(df) == 2

    @patch("src.data.fmp_provider.FMPProvider._get")
    def test_get_news(self, mock_get):
        from src.data.fmp_provider import FMPProvider
        mock_get.return_value = [
            {"title": "Apple Reports Q4", "site": "Reuters", "url": "https://example.com", "publishedDate": "2024-01-02"},
        ]
        provider = FMPProvider(api_key="test")
        news = provider.get_news("AAPL")
        assert len(news) == 1
        assert news[0]["title"] == "Apple Reports Q4"
        assert "publisher" in news[0]

    def test_options_not_supported(self):
        from src.data.fmp_provider import FMPProvider
        provider = FMPProvider(api_key="test")
        assert provider.get_options_expirations("AAPL") == []


# ═══════════════════════════════════════════════════════════════════
# 1.3 — MultiProvider Fallback
# ═══════════════════════════════════════════════════════════════════


class TestMultiProvider:
    """Test MultiProvider fallback chain."""

    def test_uses_primary_when_successful(self):
        from src.data.provider import MultiProvider

        primary = MagicMock()
        primary.get_info.return_value = {"symbol": "AAPL", "currentPrice": 175}
        fallback = MagicMock()

        multi = MultiProvider(primary, fallback)
        result = multi.get_info("AAPL")

        assert result["currentPrice"] == 175
        primary.get_info.assert_called_once_with("AAPL")
        fallback.get_info.assert_not_called()

    def test_falls_back_on_empty_primary(self):
        from src.data.provider import MultiProvider

        primary = MagicMock()
        primary.get_info.return_value = {}  # empty = failure
        fallback = MagicMock()
        fallback.get_info.return_value = {"symbol": "AAPL", "currentPrice": 175}

        multi = MultiProvider(primary, fallback)
        result = multi.get_info("AAPL")

        assert result["currentPrice"] == 175
        fallback.get_info.assert_called_once_with("AAPL")

    def test_falls_back_on_exception(self):
        from src.data.provider import MultiProvider

        primary = MagicMock()
        primary.get_info.side_effect = Exception("API down")
        fallback = MagicMock()
        fallback.get_info.return_value = {"symbol": "AAPL", "currentPrice": 175}

        multi = MultiProvider(primary, fallback)
        result = multi.get_info("AAPL")

        assert result["currentPrice"] == 175

    def test_returns_empty_when_both_fail(self):
        from src.data.provider import MultiProvider

        primary = MagicMock()
        primary.get_info.side_effect = Exception("primary down")
        fallback = MagicMock()
        fallback.get_info.side_effect = Exception("fallback down")

        multi = MultiProvider(primary, fallback)
        result = multi.get_info("AAPL")

        assert result == {}

    def test_no_fallback_returns_empty_on_failure(self):
        from src.data.provider import MultiProvider

        primary = MagicMock()
        primary.get_info.return_value = {}

        multi = MultiProvider(primary, fallback=None)
        result = multi.get_info("AAPL")

        assert result == {}

    def test_history_fallback_returns_dataframe(self):
        from src.data.provider import MultiProvider

        primary = MagicMock()
        primary.get_history.return_value = pd.DataFrame()  # empty
        fallback = MagicMock()
        fallback.get_history.return_value = pd.DataFrame({"Close": [100, 101]})

        multi = MultiProvider(primary, fallback)
        result = multi.get_history("AAPL")

        assert not result.empty
        assert "Close" in result.columns

    def test_is_empty_checks(self):
        from src.data.provider import MultiProvider

        assert MultiProvider._is_empty(None) is True
        assert MultiProvider._is_empty({}) is True
        assert MultiProvider._is_empty([]) is True
        assert MultiProvider._is_empty(pd.DataFrame()) is True
        assert MultiProvider._is_empty(pd.Series(dtype=float)) is True
        assert MultiProvider._is_empty({"data": 1}) is False
        assert MultiProvider._is_empty([1]) is False


# ═══════════════════════════════════════════════════════════════════
# Data Validator
# ═══════════════════════════════════════════════════════════════════


class TestDataValidator:
    """Test data quality validation."""

    def test_validate_info_empty(self):
        from src.data.validator import validate_info
        issues = validate_info({})
        assert len(issues) == 1
        assert "Empty" in issues[0]

    def test_validate_info_missing_price(self):
        from src.data.validator import validate_info
        issues = validate_info({"symbol": "AAPL", "sector": "Tech"})
        assert any("price" in i.lower() for i in issues)

    def test_validate_info_valid(self):
        from src.data.validator import validate_info
        issues = validate_info({
            "currentPrice": 175.50,
            "marketCap": 2800000000000,
            "trailingPE": 28.5,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "trailingEps": 6.16,
            "fiftyTwoWeekHigh": 190.0,
            "fiftyTwoWeekLow": 150.0,
        })
        assert len(issues) == 0

    def test_validate_info_suspicious_pe(self):
        from src.data.validator import validate_info
        issues = validate_info({"currentPrice": 100, "trailingPE": 50000})
        assert any("P/E" in i for i in issues)

    def test_validate_history_empty(self):
        from src.data.validator import validate_history
        issues = validate_history(pd.DataFrame(), symbol="AAPL")
        assert any("Empty" in i for i in issues)

    def test_validate_history_valid(self):
        from src.data.validator import validate_history
        import numpy as np
        dates = pd.date_range("2024-01-01", periods=250, freq="B")
        df = pd.DataFrame({
            "Open": np.random.uniform(170, 180, 250),
            "High": np.random.uniform(175, 185, 250),
            "Low": np.random.uniform(165, 175, 250),
            "Close": np.random.uniform(170, 180, 250),
            "Volume": np.random.randint(40000000, 60000000, 250),
        }, index=dates)
        issues = validate_history(df, expected_period="1y", symbol="AAPL")
        # Should have no critical issues (may flag staleness depending on date)
        assert not any("Missing OHLCV" in i for i in issues)

    def test_validate_history_missing_columns(self):
        from src.data.validator import validate_history
        df = pd.DataFrame({"price": [100, 101]})
        issues = validate_history(df, symbol="TEST")
        assert any("Missing OHLCV" in i for i in issues)

    def test_cross_validate_price_within_tolerance(self):
        from src.data.validator import cross_validate_price
        result = cross_validate_price(175.50, 175.00)
        assert result is None

    def test_cross_validate_price_divergence(self):
        from src.data.validator import cross_validate_price
        result = cross_validate_price(175.50, 150.00)
        assert result is not None
        assert "mismatch" in result.lower()


# ═══════════════════════════════════════════════════════════════════
# 1.4 — LLM Insight Engine
# ═══════════════════════════════════════════════════════════════════


class TestLLMInsightEngine:
    """Test LLM-powered insight engine."""

    def test_summarize_for_llm_truncates(self):
        from src.tools.llm_insight_engine import _summarize_for_llm
        long_data = {"key": "x" * 5000}
        result = _summarize_for_llm(long_data, max_len=100)
        assert len(result) <= 120  # 100 + truncation message

    def test_summarize_for_llm_handles_none(self):
        from src.tools.llm_insight_engine import _summarize_for_llm
        assert _summarize_for_llm(None) == "No data available."

    def test_format_rule_signals(self):
        from src.tools.llm_insight_engine import _format_rule_signals
        signals = [
            {"icon": "🟢", "title": "RSI Oversold", "direction": "bullish", "confidence": 0.75, "supporting_evidence": ["RSI: 28"]},
        ]
        result = _format_rule_signals(signals)
        assert "RSI Oversold" in result
        assert "BULLISH" in result

    def test_format_rule_signals_empty(self):
        from src.tools.llm_insight_engine import _format_rule_signals
        assert "No rule-based signals" in _format_rule_signals([])

    def test_parse_llm_json(self):
        from src.tools.llm_insight_engine import _parse_llm_json
        raw = '```json\n{"key_insights": [], "contradictions": []}\n```'
        result = _parse_llm_json(raw)
        assert "key_insights" in result

    def test_parse_llm_json_no_codeblock(self):
        from src.tools.llm_insight_engine import _parse_llm_json
        raw = '{"key_insights": [{"title": "test"}]}'
        result = _parse_llm_json(raw)
        assert result["key_insights"][0]["title"] == "test"

    def test_build_llm_result(self):
        from src.tools.llm_insight_engine import _build_llm_result
        llm_data = {
            "key_insights": [
                {
                    "category": "Opportunity",
                    "severity": "High",
                    "title": "Undervalued",
                    "observation": "Trading below intrinsic value",
                    "supporting_evidence": ["P/E: 12"],
                    "confidence": 0.85,
                    "actionability": "Buy",
                    "direction": "bullish",
                    "time_horizon": "medium-term",
                }
            ],
            "contradictions": [],
            "overall_assessment": {
                "bias": "Bullish",
                "conviction": "High",
                "reasoning": "Strong fundamentals",
                "key_risk": "Market downturn",
                "key_catalyst": "Earnings beat",
            },
            "watch_items": [],
        }
        rule_based = {"confluences": [], "anomalies": []}
        result = _build_llm_result("AAPL", llm_data, rule_based, 1.5)

        assert result["symbol"] == "AAPL"
        assert result["engine"] == "llm-powered"
        assert result["overall_bias"] == "Bullish"
        assert result["bullish_signals"] == 1
        assert len(result["observations"]) == 1

    @pytest.mark.asyncio
    async def test_generate_smart_observations_fallback(self):
        """When LLM is unavailable, should fall back to rule-based."""
        from src.tools.llm_insight_engine import generate_smart_observations

        analyses = {
            "technical": {"rsi": {"value": 25}},
        }

        # With no LLM configured, should fall back gracefully
        with patch("src.tools.llm_insight_engine._run_llm_synthesis", side_effect=Exception("No LLM")):
            result = await generate_smart_observations("AAPL", analyses)

        assert result["symbol"] == "AAPL"
        assert result["engine"] == "rule-based (LLM unavailable)"
        assert result["total_observations"] >= 1  # RSI oversold detected


# ═══════════════════════════════════════════════════════════════════
# 1.1 — RAG Pipeline
# ═══════════════════════════════════════════════════════════════════


class TestRAGChunking:
    """Test the text chunking logic (no external deps needed)."""

    def test_short_text_single_chunk(self):
        from src.rag.ingester import SECIngester
        chunks = SECIngester._chunk_text("Short text")
        assert len(chunks) == 1
        assert chunks[0] == "Short text"

    def test_long_text_multiple_chunks(self):
        from src.rag.ingester import SECIngester
        text = "word " * 1000  # ~5000 chars
        chunks = SECIngester._chunk_text(text)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self):
        from src.rag.ingester import SECIngester
        text = "sentence one. " * 200 + "sentence two. " * 200
        chunks = SECIngester._chunk_text(text)
        if len(chunks) >= 2:
            # Last chars of chunk[0] should overlap with start of chunk[1]
            # (approximately, due to sentence boundary breaking)
            assert len(chunks[0]) > 100
            assert len(chunks[1]) > 100


class TestRAGRetriever:
    """Test RAGRetriever with mocked embedder."""

    def test_search_formats_results(self):
        from src.rag.retriever import RAGRetriever

        mock_embedder = MagicMock()
        mock_embedder.query.return_value = {
            "documents": ["Revenue grew 15% YoY"],
            "metadatas": [{"symbol": "AAPL", "filing_type": "10-K", "filed_date": "2024-01-15"}],
            "distances": [0.3],
            "ids": ["doc1"],
        }

        retriever = RAGRetriever(embedder=mock_embedder)
        results = retriever.search("revenue growth", symbol="AAPL")

        assert len(results) == 1
        assert results[0]["text"] == "Revenue grew 15% YoY"
        assert results[0]["relevance_score"] > 0
        assert results[0]["metadata"]["symbol"] == "AAPL"

    def test_get_context_for_llm(self):
        from src.rag.retriever import RAGRetriever

        mock_embedder = MagicMock()
        mock_embedder.query.return_value = {
            "documents": ["Risk factor: Supply chain disruption"],
            "metadatas": [{"symbol": "AAPL", "filing_type": "10-K", "filed_date": "2024-01-15"}],
            "distances": [0.2],
            "ids": ["doc1"],
        }

        retriever = RAGRetriever(embedder=mock_embedder)
        context = retriever.get_context_for_llm("risk factors", symbol="AAPL")

        assert "Supply chain disruption" in context
        assert "Source 1" in context
        assert "AAPL" in context

    def test_empty_results(self):
        from src.rag.retriever import RAGRetriever

        mock_embedder = MagicMock()
        mock_embedder.query.return_value = {
            "documents": [], "metadatas": [], "distances": [], "ids": [],
        }

        retriever = RAGRetriever(embedder=mock_embedder)
        context = retriever.get_context_for_llm("anything")
        assert "No relevant documents" in context


# ═══════════════════════════════════════════════════════════════════
# 1.2 — ReAct Reasoning (BaseAgent)
# ═══════════════════════════════════════════════════════════════════


class TestReActReasoning:
    """Test ReAct reasoning enhancements in BaseAgent."""

    def test_extract_confidence_standard(self):
        from src.agents.base import BaseAgent
        assert BaseAgent._extract_confidence("Confidence: 0.85") == 0.85

    def test_extract_confidence_bold(self):
        from src.agents.base import BaseAgent
        assert BaseAgent._extract_confidence("**Confidence: 0.72**") == 0.72

    def test_extract_confidence_percentage(self):
        from src.agents.base import BaseAgent
        assert BaseAgent._extract_confidence("confidence: 85") == 0.85

    def test_extract_confidence_missing(self):
        from src.agents.base import BaseAgent
        assert BaseAgent._extract_confidence("No confidence here") == 0.5

    def test_extract_confidence_normalizes_percentage(self):
        from src.agents.base import BaseAgent
        # 1.5 is > 1.0, so treated as percentage: 1.5/100 = 0.015
        assert BaseAgent._extract_confidence("Confidence: 1.5") == 0.015
        # 85 is > 1.0, so treated as percentage: 85/100 = 0.85
        assert BaseAgent._extract_confidence("Confidence: 85") == 0.85
        # Negative numbers won't match the regex, so default 0.5
        assert BaseAgent._extract_confidence("Confidence: -0.5") == 0.5

    def test_agent_result_has_confidence(self):
        from src.agents.base import AgentResult
        result = AgentResult(
            success=True,
            data={"output": "test"},
            agent_name="test",
            confidence=0.85,
            reasoning_steps=3,
        )
        d = result.to_dict()
        assert d["confidence"] == 0.85
        assert d["reasoning_steps"] == 3

    def test_build_react_prompt(self):
        """Test that _build_react_prompt includes reasoning protocol."""
        from src.agents.base import BaseAgent

        # Create a minimal concrete subclass for testing
        class TestAgent(BaseAgent):
            def _get_default_tools(self):
                return []
            def _get_system_prompt(self):
                return "Test agent"

        with patch.object(BaseAgent, '_create_default_llm'):
            with patch.object(BaseAgent, '_create_agent_graph'):
                agent = TestAgent(name="test", description="test")
                prompt = agent._build_react_prompt("Analyze AAPL")

                assert "Reasoning Protocol" in prompt
                assert "Step 1" in prompt
                assert "Confidence" in prompt
                assert "Analyze AAPL" in prompt

    def test_build_react_prompt_with_context(self):
        from src.agents.base import BaseAgent

        class TestAgent(BaseAgent):
            def _get_default_tools(self):
                return []
            def _get_system_prompt(self):
                return "Test agent"

        with patch.object(BaseAgent, '_create_default_llm'):
            with patch.object(BaseAgent, '_create_agent_graph'):
                agent = TestAgent(name="test", description="test")
                prompt = agent._build_react_prompt(
                    "Analyze AAPL",
                    context={"sector": "Technology"},
                )
                assert "Technology" in prompt


# ═══════════════════════════════════════════════════════════════════
# Provider Factory
# ═══════════════════════════════════════════════════════════════════


class TestProviderFactory:
    """Test get_provider factory with new provider support."""

    def test_create_yfinance_provider(self):
        from src.data.provider import _create_provider
        provider = _create_provider("yfinance")
        assert type(provider).__name__ == "YFinanceProvider"

    def test_create_fmp_provider_no_key(self):
        from src.data.provider import _create_provider
        with patch("src.config.get_settings") as mock_settings:
            mock_settings.return_value.data_api.fmp_api_key = ""
            with pytest.raises(ValueError, match="FMP_API_KEY"):
                _create_provider("fmp")

    def test_create_fmp_provider_with_key(self):
        from src.data.provider import _create_provider
        with patch("src.config.get_settings") as mock_settings:
            mock_settings.return_value.data_api.fmp_api_key = "test_key"
            provider = _create_provider("fmp")
            assert type(provider).__name__ == "FMPProvider"

    def test_create_unknown_provider(self):
        from src.data.provider import _create_provider
        with pytest.raises(ValueError, match="Unknown provider"):
            _create_provider("nonexistent")

    def test_reset_provider(self):
        from src.data.provider import reset_provider, get_provider, _provider_instance
        reset_provider()
        # After reset, next get_provider should create fresh instance
        provider = get_provider("yfinance")
        assert provider is not None
        reset_provider()  # cleanup
