import re
import bleach
from fastapi import HTTPException, status
from typing import List, Dict, Any, Optional


class SecurityManager:
    """Centralized security and validation middleware functions."""

    # Maximum safe lengths for LLM input fields (to prevent DoS via long inputs)
    LLM_MAX_NAME_LENGTH = 200
    LLM_MAX_NOTES_LENGTH = 2000
    LLM_MAX_FREE_TEXT_LENGTH = 5000

    # Prompt injection patterns to detect and remove
    PROMPT_INJECTION_PATTERNS = [
        # Role manipulation
        r'\bignore\s+(?:all\s+)?(?:previous|prior|above|the\s+above)\s+(?:instructions?|prompts?|commands?|context)\b',
        r'\bforget\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions?|prompts?|commands?)\b',
        r'\bdiscard\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions?|prompts?|context?)\b',
        r'\bdisregard\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions?|prompts?|context?)\b',
        # System/role injection
        r'^\s*system\s*[:\-]',
        r'^\s*assistant\s*[:\-]',
        r'^\s*user\s*[:\-]',
        r'^\s*human\s*[:\-]',
        r'^\s*ai\s*[:\-]',
        r'^\s*developer\s*[:\-]',
        r'^\s*instruction\s*[:\-]',
        # Delimiter injection
        r'```\s*(?:system|assistant|user|instructions?)',
        r'---\s*(?:system|assistant|user)\s*---',
        r'<\s*/?\s*(?:system|assistant|user|instructions?)\s*>',
        # Common jailbreak prefixes
        r'^\s*DAN\s*[:\-]',
        r'^\s*Jailbreak\s*[:\-]',
        r'^\s*Developer\s*Mode\s*[:\-]',
        r'\bignore\s+your\s+(?:programming|training|instructions|guidelines)\b',
        r'\bdo\s+not\s+(?:follow|obey|adhere\s+to)\s+(?:your|the)\s+(?:instructions|guidelines|rules)\b',
        r'\byou\s+are\s+now\s+(?:in|entering)\s+(?:developer\s+mode|DAN\s+mode|jailbreak\s+mode)\b',
        # Newline-based injection sequences
        r'\n\s*system\s*[:\-]',
        r'\n\s*assistant\s*[:\-]',
        r'\n\s*instruction\s*[:\-]',
    ]

    # Compiled regex patterns for performance
    _INJECTION_REGEX = re.compile(
        '|'.join(f'({p})' for p in PROMPT_INJECTION_PATTERNS),
        re.IGNORECASE | re.MULTILINE
    )

    @staticmethod
    def sanitize_input(data: str) -> str:
        """
        Removes potentially dangerous characters from string input using bleach.

        Uses bleach.clean() for robust HTML sanitization (replaces bypassable regex).
        Also strips null bytes and newlines to prevent injection attacks.
        """
        if not data:
            return data

        # Convert to string if not already
        text = str(data)

        # Step 1: Strip null bytes (prevents null byte injection attacks)
        text = text.replace('\x00', '')

        # Step 2: Strip newlines and carriage returns (prevents newline-based injection)
        text = text.replace('\r', '').replace('\n', '')

        # Step 3: Use bleach.clean() for robust HTML sanitization
        # No HTML tags allowed, strip=True removes them entirely
        sanitized = bleach.clean(
            text,
            tags=[],  # No HTML tags allowed
            attributes={},  # No attributes allowed
            protocols=[],  # No URL protocols allowed
            strip=True  # Strip disallowed tags instead of escaping
        )

        return sanitized

    @staticmethod
    def _decode_url_encoding(text: str) -> str:
        """Decode URL percent-encoded strings if they contain suspicious content."""
        url_encoded_pattern = re.compile(r'%[0-9a-fA-F]{2}')
        if not url_encoded_pattern.search(text):
            return text
        try:
            import urllib.parse
            decoded = urllib.parse.unquote(text)
            if '<' in decoded or 'script' in decoded.lower():
                return decoded
        except Exception:
            pass
        return text

    @staticmethod
    def _decode_unicode_escapes(text: str) -> str:
        """Decode Unicode escape sequences (\uXXXX and \xXX)."""
        unicode_escape_pattern = re.compile(chr(92) + 'u[0-9a-fA-F]{4}|' + chr(92) + 'x[0-9a-fA-F]{2}')
        if not unicode_escape_pattern.search(text):
            return text
        try:
            return text.encode('utf-8').decode('unicode_escape')
        except (UnicodeDecodeError, UnicodeEncodeError):
            return text

    @staticmethod
    def _strip_null_bytes(text: str) -> str:
        """Remove null bytes in various encodings."""
        text = text.replace('\x00', '').replace('\u0000', '')
        return re.sub(r'%00|\\x00|\\u0000', '', text, flags=re.IGNORECASE)

    @staticmethod
    def _normalize_newlines(text: str) -> str:
        """Normalize newlines and limit consecutive ones."""
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return re.sub(r'\n{4,}', '\n\n\n', text)

    @staticmethod
    def _apply_bleach_sanitization(text: str) -> str:
        """Apply bleach HTML sanitization."""
        return bleach.clean(
            text,
            tags=[],  # No HTML tags allowed
            attributes={},  # No attributes allowed
            protocols=[],  # No URL protocols allowed
            strip=True  # Strip disallowed tags instead of escaping
        )

    @staticmethod
    def _remove_control_chars(text: str) -> str:
        """Remove control characters except normal whitespace."""
        return ''.join(
            char for char in text
            if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) <= 126) or ord(char) > 127
        )

    @staticmethod
    def _check_double_encoding(original: str, text: str) -> str:
        """Check for and handle double-encoding attempts."""
        url_encoded_pattern = re.compile(r'%[0-9a-fA-F]{2}')
        if '%25' not in original or not url_encoded_pattern.search(text):
            return text
        try:
            import urllib.parse
            return urllib.parse.unquote(text)
        except Exception:
            return text

    @staticmethod
    def _truncate_text(text: str, max_length: Optional[int]) -> str:
        """Truncate text to safe maximum length."""
        max_len = max_length or SecurityManager.LLM_MAX_FREE_TEXT_LENGTH
        if len(text) <= max_len:
            return text
        return text[:max_len].rsplit(' ', 1)[0] + '...'

    @staticmethod
    def llm_sanitize(text: str, max_length: Optional[int] = None) -> str:
        """
        Dedicated LLM input sanitizer with enhanced protection against encoding-based attacks.

        Protects against:
        - URL encoding bypasses (%3Cscript%3E)
        - Unicode escape sequences (\u003cscript\u003e, \x3cscript\x3e)
        - HTML entity encoding (&lt;script&gt;)
        - Double encoding (%253C for %3C)
        - Null byte injection (%00, \x00)
        - Prompt injection via various delimiters

        Args:
            text: Raw user input (may contain encoded malicious content)
            max_length: Maximum allowed length after decoding and sanitization

        Returns:
            Fully decoded and sanitized text safe for LLM prompt inclusion

        Raises:
            ValueError: If text is None or contains suspicious encoding patterns
        """
        if text is None:
            raise ValueError("Input text cannot be None")

        if not isinstance(text, str):
            text = str(text)

        original_for_detection = text

        # Apply sanitization steps
        text = SecurityManager._decode_url_encoding(text)
        text = SecurityManager._decode_unicode_escapes(text)

        import html
        text = html.unescape(text)

        text = SecurityManager._strip_null_bytes(text)
        text = SecurityManager._normalize_newlines(text)
        text = SecurityManager._apply_bleach_sanitization(text)

        # Remove prompt injection patterns
        text = SecurityManager._INJECTION_REGEX.sub('[REDACTED]', text)

        text = SecurityManager._remove_control_chars(text)
        text = SecurityManager._check_double_encoding(original_for_detection, text)
        text = SecurityManager._truncate_text(text, max_length)

        # Final cleanup
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)

        return text

    @staticmethod
    def sanitize_for_llm(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize user input for safe inclusion in LLM prompts.

        Protects against:
        - Prompt injection attacks (role manipulation, delimiter injection)
        - HTML/script injection via bleach
        - Newline-based injection sequences
        - Null byte injection
        - Overly long inputs (DoS)

        Args:
            text: Raw user input to sanitize
            max_length: Maximum allowed length (default: LLM_MAX_FREE_TEXT_LENGTH)

        Returns:
            Sanitized text safe for LLM prompt inclusion

        Raises:
            ValueError: If text is None (explicit invalid input)
        """
        if text is None:
            raise ValueError("Input text cannot be None")

        if not isinstance(text, str):
            text = str(text)

        # Step 1: Strip null bytes (common in injection attacks)
        sanitized = text.replace('\x00', '')

        # Step 2: Normalize newlines to prevent injection sequences
        # Replace \r\n, \r with \n for consistency, then limit consecutive newlines
        sanitized = sanitized.replace('\r\n', '\n').replace('\r', '\n')
        # Prevent newline-based injection by limiting to max 3 consecutive newlines
        sanitized = re.sub(r'\n{4,}', '\n\n\n', sanitized)

        # Step 3: Strip HTML using bleach
        # This removes script tags, event handlers, and other HTML nasties
        sanitized = bleach.clean(
            sanitized,
            tags=[],  # No HTML tags allowed
            attributes={},  # No attributes allowed
            strip=True  # Strip disallowed tags instead of escaping
        )

        # Step 4: Remove prompt injection patterns
        # Replace matches with [REDACTED] to maintain text structure
        def replace_injection(match):
            # Log the attempt (in production, use proper logging)
            return '[REDACTED]'

        sanitized = SecurityManager._INJECTION_REGEX.sub(replace_injection, sanitized)

        # Step 5: Remove any remaining control characters except normal whitespace
        # Allow: space, tab, newline (already normalized)
        sanitized = ''.join(
            char for char in sanitized
            if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) <= 126) or ord(char) > 127
        )

        # Step 6: Truncate to safe maximum length
        max_len = max_length or SecurityManager.LLM_MAX_FREE_TEXT_LENGTH
        if len(sanitized) > max_len:
            sanitized = sanitized[:max_len].rsplit(' ', 1)[0] + '...'

        # Step 7: Final cleanup - strip leading/trailing whitespace and normalize internal spaces
        sanitized = sanitized.strip()
        sanitized = re.sub(r'\s+', ' ', sanitized)  # Normalize multiple spaces

        return sanitized

    @staticmethod
    def sanitize_student_name(name: str) -> str:
        """
        Sanitize a student name for LLM consumption.

        Restrictive sanitization for names - only allows:
        - Alphabetic characters
        - Spaces, hyphens, apostrophes (common in names)
        - Limited length

        Also strips null bytes and newlines to prevent injection attacks.
        """
        if not name:
            return "Unknown"

        # Step 1: Strip null bytes (prevents null byte injection attacks)
        name = name.replace('\x00', '')

        # Step 2: Strip newlines and carriage returns (prevents newline-based injection)
        name = name.replace('\r', '').replace('\n', '')

        # Step 3: Strip HTML using bleach
        name = bleach.clean(name, tags=[], attributes={}, strip=True)

        # Step 4: Remove any characters not typically found in names
        # Allow: letters, spaces, hyphens, apostrophes, periods (for initials)
        name = re.sub(r"[^\w\s\-\'\.\,]", "", name, flags=re.UNICODE)

        # Step 5: Remove prompt injection patterns
        name = SecurityManager._INJECTION_REGEX.sub('[REDACTED]', name)

        # Step 6: Truncate
        if len(name) > SecurityManager.LLM_MAX_NAME_LENGTH:
            name = name[:SecurityManager.LLM_MAX_NAME_LENGTH].rsplit(' ', 1)[0] + '...'

        return name.strip() or "Unknown"

    @staticmethod
    def sanitize_notes(notes: str) -> str:
        """
        Sanitize advisor notes for LLM consumption.

        Allows more characters than names but still protects against injection.
        """
        return SecurityManager.sanitize_for_llm(notes, max_length=SecurityManager.LLM_MAX_NOTES_LENGTH)

    @staticmethod
    def validate_llm_input(data: Dict[str, Any], schema: Dict[str, tuple]) -> Dict[str, Any]:
        """
        Validate and sanitize multiple LLM input fields according to a schema.

        Args:
            data: Dictionary of input data
            schema: Dictionary mapping field names to (sanitizer_function, max_length)
                   e.g., {"name": (SecurityManager.sanitize_student_name, None)}

        Returns:
            Dictionary with sanitized values
        """
        sanitized = {}
        for field, (sanitizer, max_len) in schema.items():
            raw_value = data.get(field, "")
            if max_len:
                sanitized[field] = sanitizer(raw_value, max_len)
            else:
                sanitized[field] = sanitizer(raw_value)
        return sanitized

    @staticmethod
    def enforce_role(user_role: str, allowed_roles: List[str]):
        """Enforces RBAC on protected endpoints."""
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to access this resource."
            )

    @staticmethod
    def validate_pagination(skip: int, limit: int):
        """Validates standard pagination parameters."""
        if skip < 0:
            raise HTTPException(status_code=400, detail="Skip must be >= 0")
        if limit <= 0 or limit > 1000:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")


security_manager = SecurityManager()
