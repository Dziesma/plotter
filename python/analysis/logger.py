import logging
import os
import sys
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels."""
    
    COLORS = {
        logging.DEBUG: '\033[0;36m',    # Cyan
        logging.INFO: '\033[0;32m',     # Green  
        logging.WARNING: '\033[0;33m',  # Yellow
        logging.ERROR: '\033[0;31m',    # Red
        logging.CRITICAL: '\033[0;35m'  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelno)
        message = super().format(record)
        if color:
            message = color + message + self.RESET
        return message

class PackageLogger:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PackageLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not PackageLogger._initialized:
            self.loggers = {}
            self.log_dir = "logs"
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Set up main package logger
            self.main_logger = self._setup_logger(
                "analysis",
                os.path.join(self.log_dir, "analysis.log")
            )
            PackageLogger._initialized = True
    
    def _setup_logger(self, 
                     name: str, 
                     log_file: Optional[str] = None, 
                     level: int = logging.INFO) -> logging.Logger:
        """Internal method to set up individual loggers."""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Only add handlers if they don't exist
        if not logger.handlers:
            # Formatters
            detailed_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            colored_formatter = ColoredFormatter(
                '%(levelname)s - %(message)s'
            )
            
            # Console handler with colored output
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(colored_formatter)
            logger.addHandler(console_handler)
            
            # File handler (no colors in file)
            if log_file:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(detailed_formatter)
                logger.addHandler(file_handler)
        
        return logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger for a specific component."""
        if name not in self.loggers:
            log_file = os.path.join(self.log_dir, f"{name}.log")
            self.loggers[name] = self._setup_logger(name, log_file)
        return self.loggers[name]

# Global instance
package_logger = PackageLogger() 