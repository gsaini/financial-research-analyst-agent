"""
Tests for the agents module.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.agents.base import BaseAgent, AgentResult, AgentState
from src.agents.data_collector import DataCollectorAgent
from src.agents.technical import TechnicalAnalystAgent
from src.agents.fundamental import FundamentalAnalystAgent
from src.agents.sentiment import SentimentAnalystAgent
from src.agents.risk import RiskAnalystAgent


class TestAgentState:
    """Tests for AgentState model."""
    
    def test_agent_state_creation(self):
        """Test creating an agent state."""
        state = AgentState(agent_name="TestAgent")
        assert state.agent_name == "TestAgent"
        assert state.status == "idle"
        assert state.current_task is None
        assert state.messages == []
        assert state.results == {}
    
    def test_agent_state_update(self):
        """Test updating agent state."""
        state = AgentState(agent_name="TestAgent")
        state.status = "running"
        state.current_task = "Analyze AAPL"
        
        assert state.status == "running"
        assert state.current_task == "Analyze AAPL"


class TestAgentResult:
    """Tests for AgentResult model."""
    
    def test_agent_result_success(self):
        """Test successful agent result."""
        result = AgentResult(
            success=True,
            data={"output": "Analysis complete"},
            agent_name="TestAgent",
            execution_time_seconds=1.5,
        )
        
        assert result.success is True
        assert result.error is None
        assert result.data["output"] == "Analysis complete"
    
    def test_agent_result_failure(self):
        """Test failed agent result."""
        result = AgentResult(
            success=False,
            error="API error",
            agent_name="TestAgent",
        )
        
        assert result.success is False
        assert result.error == "API error"
    
    def test_agent_result_to_dict(self):
        """Test converting result to dictionary."""
        result = AgentResult(
            success=True,
            data={"key": "value"},
            agent_name="TestAgent",
        )
        
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert "timestamp" in result_dict


class TestDataCollectorAgent:
    """Tests for DataCollectorAgent."""
    
    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        with patch('src.agents.base.ChatOpenAI'):
            agent = DataCollectorAgent()
            
            assert agent.name == "DataCollector"
            assert agent.state.status == "idle"
    
    def test_agent_has_tools(self):
        """Test agent has required tools."""
        with patch('src.agents.base.ChatOpenAI'):
            agent = DataCollectorAgent()
            
            tool_names = [t.name for t in agent.tools]
            assert "get_stock_price" in tool_names
            assert "get_historical_data" in tool_names


class TestTechnicalAnalystAgent:
    """Tests for TechnicalAnalystAgent."""
    
    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        with patch('src.agents.base.ChatOpenAI'):
            agent = TechnicalAnalystAgent()
            
            assert agent.name == "TechnicalAnalyst"
    
    def test_generate_signals(self):
        """Test signal generation from indicators."""
        with patch('src.agents.base.ChatOpenAI'):
            agent = TechnicalAnalystAgent()
            
            indicators = {
                "rsi": {"value": 25},
                "macd": {"histogram": 0.5, "crossover": "bullish"},
                "moving_averages": {"sma_200": 150},
                "current_price": 160,
            }
            
            signals = agent.generate_signals(indicators)
            
            assert "overall" in signals
            assert "confidence" in signals
            assert "individual_signals" in signals


class TestRiskAnalystAgent:
    """Tests for RiskAnalystAgent."""
    
    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        with patch('src.agents.base.ChatOpenAI'):
            agent = RiskAnalystAgent()
            
            assert agent.name == "RiskAnalyst"
    
    def test_agent_has_risk_tools(self):
        """Test agent has risk calculation tools."""
        with patch('src.agents.base.ChatOpenAI'):
            agent = RiskAnalystAgent()
            
            tool_names = [t.name for t in agent.tools]
            assert "calculate_volatility" in tool_names
            assert "calculate_var" in tool_names
            assert "calculate_sharpe_ratio" in tool_names


class TestFundamentalAnalystAgent:
    """Tests for FundamentalAnalystAgent."""
    
    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        with patch('src.agents.base.ChatOpenAI'):
            agent = FundamentalAnalystAgent()
            
            assert agent.name == "FundamentalAnalyst"
    
    def test_calculate_intrinsic_value(self):
        """Test intrinsic value calculation."""
        with patch('src.agents.base.ChatOpenAI'):
            agent = FundamentalAnalystAgent()
            
            financial_data = {
                "free_cash_flow": 100000000,
                "growth_rate": 0.10,
                "shares_outstanding": 1000000,
                "current_price": 150,
            }
            
            result = agent.calculate_intrinsic_value(financial_data, method="dcf")
            
            assert "intrinsic_value" in result
            assert "margin_of_safety" in result
            assert "recommendation" in result


class TestSentimentAnalystAgent:
    """Tests for SentimentAnalystAgent."""
    
    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        with patch('src.agents.base.ChatOpenAI'):
            agent = SentimentAnalystAgent()
            
            assert agent.name == "SentimentAnalyst"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
