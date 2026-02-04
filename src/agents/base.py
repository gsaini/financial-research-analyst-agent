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
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from pydantic import BaseModel, Field

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
    
    class Config:
        arbitrary_types_allowed = True


class AgentResult(BaseModel):
    """Model representing the result of an agent execution."""
    
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    agent_name: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_seconds": self.execution_time_seconds,
            "agent_name": self.agent_name,
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
    
    def __init__(
        self,
        name: str,
        description: str,
        llm: Optional[BaseChatModel] = None,
        tools: Optional[List[BaseTool]] = None,
        temperature: float = 0.1,
        verbose: bool = False,
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
        """
        self.name = name
        self.description = description
        self.temperature = temperature
        self.verbose = verbose
        
        # Initialize LLM
        self.llm = llm or self._create_default_llm()
        
        # Initialize tools
        self.tools = tools or self._get_default_tools()
        
        # Initialize state
        self.state = AgentState(agent_name=name)
        
        # Create agent executor
        self.agent_executor = self._create_agent_executor()
        
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
                api_key="lm-studio",  # LM Studio doesn't require real API key
            )
        elif provider == "vllm":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.llm.vllm_model,
                base_url=settings.llm.vllm_base_url,
                temperature=self.temperature,
                api_key="vllm",  # vLLM uses OpenAI-compatible API
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
            # Default to Ollama (open source)
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
    
    def _create_agent_executor(self) -> Optional[AgentExecutor]:
        """Create the agent executor with tools."""
        if not self.tools:
            logger.warning(f"No tools configured for agent: {self.name}")
            return None

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Use generic tool calling agent (works with Ollama, OpenAI, etc.)
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=self.verbose,
            max_iterations=settings.agent.max_iterations,
            handle_parsing_errors=True,
        )
    
    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[BaseMessage]] = None,
    ) -> AgentResult:
        """
        Execute a task with the agent.
        
        Args:
            task: The task to execute
            context: Additional context for the task
            chat_history: Previous conversation history
            
        Returns:
            AgentResult with execution results
        """
        start_time = datetime.utcnow()
        self.state.status = "running"
        self.state.current_task = task
        self.state.started_at = start_time
        
        try:
            logger.info(f"Agent {self.name} executing task: {task[:100]}...")
            
            # Prepare input
            agent_input = {"input": task}
            if chat_history:
                agent_input["chat_history"] = chat_history
            if context:
                agent_input["context"] = json.dumps(context)
            
            # Execute
            if self.agent_executor:
                result = await self.agent_executor.ainvoke(agent_input)
                output = result.get("output", "")
            else:
                # Direct LLM call if no tools
                messages = [
                    SystemMessage(content=self._get_system_prompt()),
                    HumanMessage(content=task),
                ]
                response = await self.llm.ainvoke(messages)
                output = response.content
            
            # Process result
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.state.status = "completed"
            self.state.completed_at = datetime.utcnow()
            self.state.results[task[:50]] = output
            
            return AgentResult(
                success=True,
                data={"output": output, "raw_result": result if self.agent_executor else None},
                execution_time_seconds=execution_time,
                agent_name=self.name,
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
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
            # If already in async context, create new loop
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
