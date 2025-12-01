import os
import logging
import traceback
from datetime import datetime

class GameLogger:
    def __init__(self, log_dir="game/logs"):
        self.log_dir = log_dir
        self.logger = None
        self._setup_logger()

    def _setup_logger(self):
        # 1. Ensure Log Directory Exists
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
            except OSError as e:
                print(f"CRITICAL: Could not create log directory {self.log_dir}: {e}")
                return

        # 2. Generate Timestamped Filename
        # Format: log_YYYYMMDD_HHMMSS.txt
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"log_{timestamp}.txt"
        log_path = os.path.join(self.log_dir, log_filename)

        # 3. Configure the Logger
        self.logger = logging.getLogger("BitRotGame")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers if re-initialized to avoid duplicate logs
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # -- File Handler (Writes to disk) --
        try:
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(logging.DEBUG)
            # Format: [Time] [Level] Message
            file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"CRITICAL: Failed to setup file logger: {e}")

        # -- Console Handler (Prints to terminal) --
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO) # Only show INFO+ to console to keep it clean
        console_formatter = logging.Formatter('[LOG] %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        self.info(f"Logger initialized. Output file: {log_path}")

    def info(self, message):
        """Log general game actions."""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)

    def warning(self, message):
        """Log suspicious behavior or non-critical issues."""
        if self.logger:
            self.logger.warning(message)
        else:
            print(f"WARNING: {message}")

    def error(self, message, exc_info=None):
        """Log errors that don't crash the game."""
        if self.logger:
            self.logger.error(message, exc_info=exc_info)
        else:
            print(f"ERROR: {message}")

    def crash(self, message, exception):
        """Log critical crashes with full traceback."""
        if self.logger:
            self.logger.critical(f"{message}\n{traceback.format_exc()}")
        else:
            print(f"CRITICAL CRASH: {message}")
            traceback.print_exc()