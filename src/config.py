"""
Configuration management for the Financial Research Analyst Agent.

This module handles loading and validating configuration from environment
variables and configuration files.
"""

import os
from pathlib import Path
from typing import List, Optional
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """LLM-related configuration settings."""
    
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    model: str = Field(default="gpt-4-turbo-preview", env="LLM_MODEL")
    temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    max_tokens: int = Field(default=4096, env="LLM_MAX_TOKENS")
    
    class Config:
        env_prefix = ""


class DataAPISettings(BaseSettings):
    """Financial data API configuration settings."""
    
    alpha_vantage_api_key: str = Field(default="", env="ALPHA_VANTAGE_API_KEY")
    finnhub_api_key: str = Field(default="", env="FINNHUB_API_KEY")
    news_api_key: str = Field(default="", env="NEWS_API_KEY")
    
    class Config:
        env_prefix = ""


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    database_url: str = Field(
        default="sqlite:///./data/financial_agent.db",
        env="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    class Config:
        env_prefix = ""


class VectorStoreSettings(BaseSettings):
    """Vector store configuration settings."""
    
    chroma_persist_dir: str = Field(default="./data/chroma", env="CHROMA_PERSIST_DIR")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        env="EMBEDDING_MODEL"
    )
    
    class Config:
        env_prefix = ""


class AgentSettings(BaseSettings):
    """Agent behavior configuration settings."""
    
    max_iterations: int = Field(default=10, env="AGENT_MAX_ITERATIONS")
    timeout_seconds: int = Field(default=300, env="AGENT_TIMEOUT_SECONDS")
    enable_memory: bool = Field(default=True, env="ENABLE_MEMORY")
    
    class Config:
        env_prefix = ""


class APISettings(BaseSettings):
    """API server configuration settings."""
    
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    reload: bool = Field(default=True, env="API_RELOAD")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    
    class Config:
        env_prefix = ""


class Settings(BaseSettings):
    """Main application settings combining all sub-settings."""
    
    # Application
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="./logs/app.log", env="LOG_FILE")
    secret_key: str = Field(default="changeme", env="SECRET_KEY")
    
    # Sub-settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    data_api: DataAPISettings = Field(default_factory=DataAPISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    api: APISettings = Field(default_factory=APISettings)
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, env="RATE_LIMIT_WINDOW_SECONDS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent
    
    @property
    def data_dir(self) -> Path:
        """Get the data directory path."""
        data_path = self.project_root / "data"
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path
    
    @property
    def logs_dir(self) -> Path:
        """Get the logs directory path."""
        logs_path = self.project_root / "logs"
        logs_path.mkdir(parents=True, exist_ok=True)
        return logs_path


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Convenience function to reload settings
def reload_settings() -> Settings:
    """
    Reload settings by clearing the cache.
    
    Returns:
        Settings: Fresh application settings instance
    """
    get_settings.cache_clear()
    return get_settings()


# Export settings instance
settings = get_settings()
