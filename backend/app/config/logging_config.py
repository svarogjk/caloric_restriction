"""
Logging configuration for GEO Analysis API
Handles both console and file logging with rotation
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent.parent / "geo_logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Log file path
LOG_FILE = LOGS_DIR / "geo_analysis.log"

def setup_logging(level=logging.INFO):
    """
    Configure logging to output to both console and file
    
    Args:
        level: Logging level (default: INFO)
    """
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File Handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=50 * 1024 * 1024,  # 50 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    root_logger.info("=" * 70)
    root_logger.info(f"Logging initialized at {datetime.now()}")
    root_logger.info(f"Log file: {LOG_FILE}")
    root_logger.info("=" * 70)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module
    
    Args:
        name: Module name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
