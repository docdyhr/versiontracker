"""Utility handlers for VersionTracker."""

import logging
import sys
import traceback
import warnings
from typing import Any, Callable, Optional


def setup_logging(
    level: int, 
    log_file: Optional[str] = None,
    warnings_file: Optional[str] = None
) -> None:
    """Configure logging for the application.
    
    Args:
        level: The logging level to use (e.g. logging.DEBUG)
        log_file: Optional path to a file for storing logs
        warnings_file: Optional path to a file for storing warnings
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Setup file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Setup warnings file handler if specified
    if warnings_file:
        warnings_handler = logging.FileHandler(warnings_file)
        warnings_handler.setLevel(logging.WARNING)
        warnings_handler.setFormatter(formatter)
        root_logger.addHandler(warnings_handler)
    
    logging.debug("Logging setup complete")


def suppress_console_warnings() -> None:
    """Suppress specific warnings from being printed to the console.
    
    This does not affect logging to warning log files.
    """
    def warning_filter(message, category, filename, lineno, file=None, line=None):
        """Custom warning filter function."""
        if filename and "versiontracker" in filename:
            # Don't suppress warnings from versiontracker code
            return True
        
        # Filter out selected warning types from other libraries and modules
        for warn_type in ["DeprecationWarning", "ResourceWarning", "UserWarning"]:
            if category.__name__ == warn_type:
                return False
        
        return True
    
    # Create warning filter class
    class WarningFilter:
        def filter(self, record):
            if record.levelno == logging.WARNING:
                return warning_filter(
                    record.getMessage(), UserWarning, record.filename, record.lineno
                )
            return True
    
    # Set warnings filter
    warnings.filterwarnings("default")
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stderr:
            handler.addFilter(WarningFilter())


def safe_function_call(
    func: Callable, 
    *args, 
    default_value: Any = None,
    error_msg: str = "Error in function call",
    **kwargs
) -> Any:
    """Safely call a function, catching and logging any exceptions.
    
    Args:
        func: The function to call
        *args: Arguments to pass to the function
        default_value: Value to return if the function call fails
        error_msg: Message to log on error
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call, or default_value if the call fails
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"{error_msg}: {e}")
        return default_value