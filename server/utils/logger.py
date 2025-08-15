import logging
import sys
from typing import Optional


def setup_logger(name: str = "ai_voice_agent", level: int = logging.INFO) -> logging.Logger:
    """Setup and configure logger for the application"""
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create console handler with a higher log level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Create formatter and add it to the handler
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(console_handler)
    
    return logger


# Create default logger instance
logger = setup_logger()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance"""
    if name:
        return logging.getLogger(f"ai_voice_agent.{name}")
    return logger
