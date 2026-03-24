from datetime import timezone
"""
Base Agent class for the Financial Research Analyst Agent.

This module provides the foundational agent class that all specialized
agents inherit from.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from pydantic import BaseModel, Field, ConfigDict

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AgentState(BaseModel):
    """Model representing the current state of an agent."""

    agent_name: str
    status: str = "idle"  # idle, running, completed, error
    current_task: Optional[str] = None
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AgentResult(BaseModel):
    """Model representing the result of an agent execution."""

    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    agent_name: str = ""
    confidence: float = Field(default=0.0, description="Confidence score 0.0-1.0")
    reasoning_steps: int = Field(default=0, description="Number of reasoning steps taken")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_seconds": self.execution_time_seconds,
            "agent_name": self.agent_name,
            "confidence": self.confidence,
            "reasoning_steps": self.reasoning_steps,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseAgent(ABC):
    """
    Base class for all financial research agents.

    This class provides common functionality for:
    - LLM initialization
    - Tool management
    - State management
    - Logging and error handling
    """

    # ReAct reasoning configuration
    MAX_REASONING_STEPS: int = 5
    CONFIDENCE_THRESHOLD: float = 0.7

    def __init__(
        self,
        name: str,
        description: str,
        llm: Optional[BaseChatModel] = None,
        tools: Optional[List[BaseTool]] = None,
        temperature: float = 0.1,
        verbose: bool = False,
        max_reasoning_steps: int = 5,
    ):
        """
        Initialize the base agent.

        Args:
            name: Agent name identifier
            description: Agent description and purpose
            llm: Language model instance (optional, will create default)
            tools: List of tools available to the agent
            temperature: LLM temperature setting
            verbose: Enable verbose logging
            max_reasoning_steps: Max ReAct reasoning iterations
        """
        self.name = name
        self.description = description
        self.temperature = temperature
        self.verbose = verbose
        self.max_reasoning_steps = max_reasoning_steps

        # Initialize LLM
        self.llm = llm or self._create_default_llm()

        # Initialize tools
        self.tools = tools or self._get_default_tools()

        # Initialize state
        self.state = AgentState(agent_name=name)

        # Create agent graph
        self.agent_graph = self._create_agent_graph()

        logger.info(f"Initialized agent: {self.name}")

    def _create_default_llm(self) -> BaseChatModel:
        """Create the default LLM instance based on configured provider."""
        provider = settings.llm.provider.lower()

        if provider == "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=settings.llm.ollama_model,
                base_url=settings.llm.ollama_base_url,
                temperature=self.temperature,
            )
        elif provider == "lmstudio":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.llm.lmstudio_model,
                base_url=settings.llm.lmstudio_base_url,
                temperature=self.temperature,
                api_key="lm-studio",
            )
        elif provider == "vllm":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.llm.vllm_model,
                base_url=settings.llm.vllm_base_url,
                temperature=self.temperature,
                api_key="vllm",
            )
        elif provider == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=settings.llm.groq_model,
                api_key=settings.llm.groq_api_key,
                temperature=self.temperature,
            )
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=settings.llm.model,
                api_key=settings.llm.anthropic_api_key,
                temperature=self.temperature,
                max_tokens=settings.llm.max_tokens,
            )
        elif provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.llm.model,
                temperature=self.temperature,
                api_key=settings.llm.openai_api_key,
                max_tokens=settings.llm.max_tokens,
            )
        else:
            from langchain_ollama import ChatOllama
            logger.warning(f"Unknown provider '{provider}', defaulting to Ollama")
            return ChatOllama(
                model=settings.llm.ollama_model,
                base_url=settings.llm.ollama_base_url,
                temperature=self.temperature,
            )

    @abstractmethod
    def _get_default_tools(self) -> List[BaseTool]:
        """
        Get the default tools for this agent.

        Returns:
            List of tools available to the agent
        """
        raise NotImplementedError("Subclasses must implement _get_default_tools")

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.

        Returns:
            System prompt string
        """
        raise NotImplementedError("Subclasses must implement _get_system_prompt")

    def _create_agent_graph(self):
        """Create the agent graph using LangChain's create_agent (LangGraph-based)."""
        return create_agent(
            model=self.llm,
            tools=self.tools or [],
            system_prompt=self._get_system_prompt(),
            name=self.name,
            debug=self.verbose,
        )

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[BaseMessage]] = None,
    ) -> AgentResult:
        """
        Execute a task with the agent using ReAct-style multi-step reasoning.

        The agent will:
        1. Think about the task and plan tool usage
        2. Execute tools and observe results
        3. Reflect on findings and assess confidence
        4. If confidence is below threshold and steps remain, investigate further
        5. Produce a final answer with confidence score

        Args:
            task: The task to execute
            context: Additional context for the task
            chat_history: Previous conversation history

        Returns:
            AgentResult with execution results and confidence score
        """
        start_time = datetime.now(timezone.utc)
        self.state.status = "running"
        self.state.current_task = task
        self.state.started_at = start_time

        try:
            logger.info(f"Agent {self.name} executing task: {task[:100]}...")

            # Build input with ReAct reasoning instructions
            input_text = self._build_react_prompt(task, context)

            # Build messages list
            messages = []
            if chat_history:
                messages.extend(chat_history)
            messages.append(HumanMessage(content=input_text))

            # Execute via agent graph (LangGraph handles tool calling loop)
            result = await self.agent_graph.ainvoke({"messages": messages})

            # Extract output and count reasoning steps
            output_messages = result.get("messages", [])
            output = ""
            reasoning_steps = 0
            for msg in reversed(output_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    output = msg.content
                    break
            # Count tool calls as reasoning steps
            for msg in output_messages:
                if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                    reasoning_steps += len(msg.tool_calls)

            # Extract confidence from output if present
            confidence = self._extract_confidence(output)

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            self.state.status = "completed"
            self.state.completed_at = datetime.now(timezone.utc)
            self.state.results[task[:50]] = output

            return AgentResult(
                success=True,
                data={"output": output, "raw_result": result},
                execution_time_seconds=execution_time,
                agent_name=self.name,
                confidence=confidence,
                reasoning_steps=reasoning_steps,
            )

        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            error_msg = str(e)

            self.state.status = "error"
            self.state.errors.append(error_msg)

            logger.error(f"Agent {self.name} error: {error_msg}")

            return AgentResult(
                success=False,
                error=error_msg,
                execution_time_seconds=execution_time,
                agent_name=self.name,
            )

    def _build_react_prompt(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build a ReAct-style prompt that encourages multi-step reasoning.

        The prompt instructs the agent to:
        1. Think step-by-step before acting
        2. Use tools to gather evidence
        3. Reflect on findings and check for contradictions
        4. Assess confidence level
        5. Investigate further if confidence is low
        """
        react_instructions = """## Reasoning Protocol

Follow this structured reasoning approach:

**Step 1 — Plan**: Before using any tools, think about what data you need and which tools to call. Identify what would increase or decrease your confidence.

**Step 2 — Gather**: Call the necessary tools to collect data and evidence.

**Step 3 — Analyze**: Examine the results. Look for:
  - Confirming signals across multiple data sources
  - Contradictions that need investigation
  - Missing data that limits your confidence
  - Non-obvious patterns or anomalies

**Step 4 — Reflect**: If your findings are contradictory or incomplete:
  - Use additional tools to investigate the contradiction
  - Look at the data from a different angle
  - Consider what alternative explanations exist

**Step 5 — Conclude**: Provide your final analysis with:
  - Clear conclusions supported by specific evidence
  - A confidence level (0.0-1.0) reflecting data quality and signal alignment
  - Key risks or caveats
  - What to watch going forward

Include a line: **Confidence: X.XX** (where X.XX is your confidence score 0.0-1.0)

---

"""
        input_text = react_instructions + task
        if context:
            input_text += f"\n\nContext: {json.dumps(context, default=str)}"
        return input_text

    @staticmethod
    def _extract_confidence(output: str) -> float:
        """Extract confidence score from agent output text."""
        import re
        # Look for patterns like "Confidence: 0.85" or "**Confidence: 0.72**"
        patterns = [
            r'\*?\*?[Cc]onfidence:?\s*\*?\*?\s*(\d+\.?\d*)',
            r'confidence[:\s]+(\d+\.?\d*)',
            r'confidence level[:\s]+(\d+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                val = float(match.group(1))
                # Normalize if given as percentage
                if val > 1.0:
                    val = val / 100.0
                return min(max(val, 0.0), 1.0)
        return 0.5  # Default confidence when not explicitly stated

    def execute_sync(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[BaseMessage]] = None,
    ) -> AgentResult:
        """
        Synchronous version of execute.

        Args:
            task: The task to execute
            context: Additional context for the task
            chat_history: Previous conversation history

        Returns:
            AgentResult with execution results
        """
        import asyncio

        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()

        return loop.run_until_complete(self.execute(task, context, chat_history))

    def reset(self) -> None:
        """Reset the agent state."""
        self.state = AgentState(agent_name=self.name)
        logger.info(f"Agent {self.name} state reset")

    def get_state(self) -> Dict[str, Any]:
        """Get the current agent state as a dictionary."""
        return self.state.model_dump()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', status='{self.state.status}')"
