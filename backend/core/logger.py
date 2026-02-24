import logging
import sys
import json
from datetime import datetime
from backend.config import LOG_LEVEL, LOG_FILE

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "module": record.module,
            "funcName": record.funcName,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logger(name: str) -> logging.Logger:
    """Sets up a structured JSON logger."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Prevent adding handlers multiple times
    if not logger.handlers:
        log_handler = logging.FileHandler(LOG_FILE)
        stream_handler = logging.StreamHandler(sys.stdout)

        formatter = JSONFormatter()

        log_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        logger.addHandler(log_handler)
        logger.addHandler(stream_handler)

    return logger

# Create a default system logger
sys_logger = setup_logger("ews_platform")

