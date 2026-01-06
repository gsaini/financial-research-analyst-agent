"""
Logging utilities for the Financial Research Analyst Agent.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from loguru import logger as loguru_logger


class InterceptHandler(logging.Handler):
    """Handler to intercept standard logging and redirect to loguru."""
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_logs: bool = False,
) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        json_logs: Whether to output logs in JSON format
    """
    # Remove default handler
    loguru_logger.remove()
    
    # Console handler
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    loguru_logger.add(
        sys.stderr,
        format=log_format,
        level=log_level,
        colorize=True,
    )
    
    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        if json_logs:
            loguru_logger.add(
                str(log_path),
                format="{message}",
                level=log_level,
                rotation="10 MB",
                retention="1 week",
                serialize=True,
            )
        else:
            loguru_logger.add(
                str(log_path),
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
                level=log_level,
                rotation="10 MB",
                retention="1 week",
            )
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Suppress noisy loggers
    for logger_name in ["httpx", "httpcore", "openai", "urllib3"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str):
    """
    Get a logger instance for a module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance
    """
    return loguru_logger.bind(name=name)


# Initialize logging on import
setup_logging()
