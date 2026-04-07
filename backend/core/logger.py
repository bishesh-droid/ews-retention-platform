import logging
import sys
import json
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from backend.config import LOG_LEVEL, LOG_FILE

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "module": record.module,
            "funcName": record.funcName,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logger(name: str) -> logging.Logger:
    """Sets up a structured JSON logger."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    logger.propagate = False

    # Reset handlers to avoid duplication in reload/test contexts.
    logger.handlers = []

    log_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5)
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = JSONFormatter()

    log_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.addHandler(log_handler)
    logger.addHandler(stream_handler)

    return logger

# Create a default system logger
sys_logger = setup_logger("ews_platform")

