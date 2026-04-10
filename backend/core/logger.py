import logging
import sys
import json
import re
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from backend.config import LOG_LEVEL, LOG_FILE


# ---------------------------------------------------------------------------
# Log Retention Policy (FERPA Compliance)
# ---------------------------------------------------------------------------
# - Log files must NOT persist longer than 7 days in development environments
# - Production logs should have automated rotation and archival with access controls
# - PII masking is applied to prevent exposure of student data in logs
# - Consider using centralized logging with retention policies for production
# ---------------------------------------------------------------------------


class PIIMaskingFilter(logging.Filter):
    """
    Masks PII (Personally Identifiable Information) in log messages.

    FERPA Compliance: Prevents student email addresses, IDs, and auth tokens
    from being written to log files in plaintext.

    Masks:
      - Email addresses: user@example.com -> us***@example.com
      - Student IDs: student_12345678 -> ***5678 (last 4 chars only)
      - JWT tokens: Removes Bearer tokens and JWT patterns entirely
    """

    # Pattern for JWT (header.payload.signature format)
    JWT_PATTERN = re.compile(
        r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',
        re.IGNORECASE
    )
    # Pattern for "Bearer <token>" (captures various token formats)
    BEARER_PATTERN = re.compile(
        r'Bearer\s+[a-zA-Z0-9_\-\.=]+',
        re.IGNORECASE
    )
    # Pattern for email addresses
    EMAIL_PATTERN = re.compile(
        r'([a-zA-Z0-9._%+-]{1,2})[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        re.IGNORECASE
    )
    # Pattern for student IDs (alphanumeric, typically 6-20 chars)
    # Matches common formats: student_12345678, STU12345678, 12345678, etc.
    STUDENT_ID_PATTERN = re.compile(
        r'(student[_-]?|stu[_-]?)?([a-zA-Z0-9]{6,20})',
        re.IGNORECASE
    )

    def mask_email(self, text: str) -> str:
        """Mask email: show first 2 chars + ***@domain.com"""
        def replace_email(match):
            prefix = match.group(1)
            domain = match.group(2)
            return f"{prefix}***@{domain}"
        return self.EMAIL_PATTERN.sub(replace_email, text)

    def mask_student_id(self, text: str) -> str:
        """Mask student ID: show last 4 chars only as ***XXXX"""
        def replace_id(match):
            prefix = match.group(1) or ""  # e.g., "student_" or "stu-"
            id_value = match.group(2)
            if len(id_value) >= 4:
                # Show only last 4 characters
                return f"{prefix}***{id_value[-4:]}"
            else:
                # For short IDs, mask completely
                return f"{prefix}***"
        return self.STUDENT_ID_PATTERN.sub(replace_id, text)

    def mask_jwt_tokens(self, text: str) -> str:
        """Strip JWT tokens and Bearer tokens from logs."""
        # First remove JWT format tokens
        text = self.JWT_PATTERN.sub('[JWT_TOKEN_REDACTED]', text)
        # Then remove Bearer tokens
        text = self.BEARER_PATTERN.sub('Bearer [TOKEN_REDACTED]', text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        """Apply PII masking to the log message."""
        original_msg = record.getMessage()

        # Apply masking in sequence
        masked_msg = self.mask_jwt_tokens(original_msg)
        masked_msg = self.mask_email(masked_msg)
        masked_msg = self.mask_student_id(masked_msg)

        # Update the record's message
        record.msg = masked_msg
        record.args = ()  # Clear args since we've processed the message

        return True


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
    """Sets up a structured JSON logger with PII masking for FERPA compliance."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    logger.propagate = False

    # Reset handlers to avoid duplication in reload/test contexts.
    logger.handlers = []

    # Create PII masking filter (applied to all handlers)
    pii_filter = PIIMaskingFilter()

    log_handler = RotatingFileHandler(LOG_FILE, maxBytes=50 * 1024 * 1024, backupCount=5)
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = JSONFormatter()

    log_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    # Apply PII masking filter to all handlers
    log_handler.addFilter(pii_filter)
    stream_handler.addFilter(pii_filter)

    logger.addHandler(log_handler)
    logger.addHandler(stream_handler)

    return logger

# Create a default system logger
sys_logger = setup_logger("ews_platform")

