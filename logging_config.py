"""
Logging configuration for DFS ServiceWatch dashboard.
Provides centralized logging setup for all modules.
"""

import logging
import sys
from datetime import datetime


def setup_logging(
    level: int = logging.INFO,
    log_file: str = None,
    format_string: str = None
) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path for log output
        format_string: Custom format string

    Returns:
        Root logger instance
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            logger.warning(f"Could not create log file: {e}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Default log format for Streamlit apps (less verbose)
STREAMLIT_LOG_FORMAT = "%(levelname)s - %(name)s: %(message)s"

# Debug log format (more verbose)
DEBUG_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"


def setup_streamlit_logging() -> logging.Logger:
    """
    Configure logging optimized for Streamlit environment.
    Uses less verbose format and INFO level by default.
    """
    return setup_logging(
        level=logging.INFO,
        format_string=STREAMLIT_LOG_FORMAT
    )


def setup_debug_logging(log_file: str = None) -> logging.Logger:
    """
    Configure verbose debug logging.

    Args:
        log_file: Optional file path for debug logs
    """
    if log_file is None:
        log_file = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    return setup_logging(
        level=logging.DEBUG,
        log_file=log_file,
        format_string=DEBUG_LOG_FORMAT
    )
