import logging
import sys
import os
from pathlib import Path

def setup_logging(level=None):
    """
    Configure logging for the application.
    Level can be set via level argument or LOG_LEVEL environment variable.
    """
    if level is None:
        level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    root_logger.addHandler(console_handler)

    # File handler (optional, if LOG_FILE is set)
    log_file = os.environ.get("LOG_FILE")
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy loggers
    logging.getLogger("moviepy").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def get_logger(name):
    """Get a named logger."""
    return logging.getLogger(name)
