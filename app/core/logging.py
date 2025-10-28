"""
Logger Configuration
Provides centralized logging setup with file and console output
"""
import logging
import logging.config
from pathlib import Path
from typing import Optional

from app.core.config import LogConfig

class LogManager:
    """Centralized logging configuration management"""
    
    def __init__(self):
        self.config = LogConfig()

    def setup_logging(self, log_file: Optional[Path] = None):
        """
        Configure logging with both file and console handlers
        
        Args:
            log_file: Optional path to log file. If not provided,
                     uses the one from config if available.
        """
        if log_file:
            self.config.FILE = log_file
            
        # Apply configuration
        logging.config.dictConfig(self.config.log_config)
        
        # Log startup message
        logger = logging.getLogger(__name__)
        logger.info("Logging configured successfully")
        if self.config.FILE:
            logger.info(f"Log file: {self.config.FILE}")

# Global logging manager instance
log_manager = LogManager()

# Global logger instance for importing in other modules
logger = logging.getLogger(__name__)

# Standalone setup function for convenience
def setup_logging(level: str = "INFO", log_file: Optional[Path] = None):
    """
    Configure application logging
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
    
    Returns:
        Logger instance
    """
    # Set the log level
    logging.basicConfig(level=getattr(logging, level.upper()))
    
    # Setup file logging if specified
    if log_file:
        log_manager.setup_logging(log_file)
    
    return logging.getLogger(__name__)