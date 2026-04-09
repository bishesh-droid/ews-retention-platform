import re
import bleach
from fastapi import HTTPException, status
from typing import List, Callable, Dict, Any, Optional

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
            styles=[],  # No CSS styles allowed
            protocols=[],  # No URL protocols allowed
            strip=True  # Strip disallowed tags instead of escaping
        )

        return sanitized

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

        # Step 1: Detect and handle URL encoding attempts
        # Check for percent-encoded strings (common bypass technique)
        url_encoded_pattern = re.compile(r'%[0-9a-fA-F]{2}')
        if url_encoded_pattern.search(text):
            # Potential URL encoding attack - log and fully sanitize
            try:
                import urllib.parse
                decoded = urllib.parse.unquote(text)
                # If decoding reveals HTML/script tags, aggressively sanitize
                if '<' in decoded or 'script' in decoded.lower():
                    text = decoded
            except Exception:
                pass  # Continue with original text if decoding fails

        # Step 2: Handle Unicode escape sequences (\u003c, \x3c, etc.)
        # These are common encoding bypass techniques
        unicode_escape_pattern = re.compile(r'\\u[0-9a-fA-F]{4}|\\x[0-9a-fA-F]{2}')
        if unicode_escape_pattern.search(text):
            try:
                # Decode unicode escapes (both \uXXXX and \xXX formats)
                decoded = text.encode('utf-8').decode('unicode_escape')
                text = decoded
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass  # Continue with original if decoding fails

        # Step 3: Decode HTML entities (&lt;, &gt;, &#60;, &#x3C;)
        import html
        text = html.unescape(text)

        # Step 4: Strip null bytes (various encodings: %00, \x00, \u0000)
        text = text.replace('\x00', '').replace('\u0000', '')
        # Also remove common null byte representations
        text = re.sub(r'%00|\\x00|\\u0000', '', text, flags=re.IGNORECASE)

        # Step 5: Normalize newlines to prevent injection sequences
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Limit consecutive newlines to prevent delimiter injection
        text = re.sub(r'\n{4,}', '\n\n\n', text)

        # Step 6: Apply bleach HTML sanitization
        text = bleach.clean(
            text,
            tags=[],  # No HTML tags allowed
            attributes={},  # No attributes allowed
            styles=[],  # No CSS styles allowed
            protocols=[],  # No URL protocols allowed
            strip=True  # Strip disallowed tags instead of escaping
        )

        # Step 7: Remove prompt injection patterns
        text = SecurityManager._INJECTION_REGEX.sub('[REDACTED]', text)

        # Step 8: Remove control characters except normal whitespace
        # Allow: space, tab, newline (already normalized), printable ASCII, extended Unicode
        text = ''.join(
            char for char in text
            if char == '\n' or char == '\t' or (ord(char) >= 32 and ord(char) <= 126) or ord(char) > 127
        )

        # Step 9: Check for double-encoding attempts (e.g., %253C which is % encoded %3C)
        # If we still see percent signs after previous decoding, it might be double-encoded
        if '%25' in original_for_detection and url_encoded_pattern.search(text):
            # Potential double encoding - apply one more round of unquoting
            try:
                import urllib.parse
                text = urllib.parse.unquote(text)
            except Exception:
                pass

        # Step 10: Truncate to safe maximum length
        max_len = max_length or SecurityManager.LLM_MAX_FREE_TEXT_LENGTH
        if len(text) > max_len:
            text = text[:max_len].rsplit(' ', 1)[0] + '...'

        # Step 11: Final cleanup
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize multiple spaces

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
