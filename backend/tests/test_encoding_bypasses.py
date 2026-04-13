"""
Test encoding-based sanitization bypass attempts.

These tests verify that the llm_sanitize() function properly handles
various encoding techniques that attackers use to bypass input validation.

Encoding attacks tested:
1. URL encoding (%3Cscript%3E)
2. Unicode escape sequences (\u003c, \x3c)
3. HTML entity encoding (&lt;script&gt;)
4. Double encoding (%253C for %3C)
5. Null byte injection (%00, \x00, \u0000)
"""

from backend.core.security import SecurityManager


class TestEncodingBypasses:
    """Test cases for encoding-based sanitization bypasses."""

    def test_url_encoding_bypass_blocked(self):
        """
        Test 1: URL encoding bypass attempts should be neutralized.

        Attackers encode malicious payloads using percent-encoding:
        - %3C = <
        - %3E = >
        - %20 = space

        These should be decoded and sanitized, removing any HTML/script content.
        """
        # URL-encoded script tag
        url_encoded = "%3Cscript%3Ealert(%27XSS%27)%3C%2Fscript%3E"
        result = SecurityManager.llm_sanitize(url_encoded)
        # Script tags and event handlers should be removed
        assert "<script>" not in result.lower()
        assert "alert" not in result.lower()
        # The output should be clean text without HTML
        assert result == "alert(XSS)" or "[REDACTED]" in result or result.strip() == ""

        # Mixed encoding with normal text
        mixed = "Hello%20%3Cb%3EWorld%3C%2Fb%3E"
        result = SecurityManager.llm_sanitize(mixed)
        assert "<b>" not in result.lower()
        assert "</b>" not in result.lower()

    def test_unicode_escape_bypass_blocked(self):
        """
        Test 2: Unicode escape sequence bypasses should be neutralized.

        Attackers use unicode escapes to hide malicious content:
        - \\u003c = <
        - \\u003e = >
        - \\x3c = <
        - \\x3e = >

        These should be decoded and sanitized.
        """
        # Unicode escape for <script>
        unicode_escaped = r"\u003cscript\u003ealert(1)\u003c/script\u003e"
        result = SecurityManager.llm_sanitize(unicode_escaped)
        assert "<script>" not in result.lower()
        assert "alert" not in result.lower()

        # Hex escape format (often used in JavaScript contexts)
        hex_escaped = r"\x3cscript\x3ealert(1)\x3c/script\x3e"
        result = SecurityManager.llm_sanitize(hex_escaped)
        assert "<script>" not in result.lower()

        # Mixed unicode and normal text
        mixed = r"Hello \u003cb\u003eWorld\u003c/b\u003e"
        result = SecurityManager.llm_sanitize(mixed)
        assert "<b>" not in result.lower()

    def test_html_entity_encoding_bypass_blocked(self):
        """
        Test 3: HTML entity encoding bypasses should be neutralized.

        Attackers encode characters as HTML entities:
        - &lt; = <
        - &gt; = >
        - &#60; = < (decimal)
        - &#x3C; = < (hex)

        These should be decoded and then sanitized.
        """
        # Named entity encoding
        html_entities = "&lt;script&gt;alert(1)&lt;/script&gt;"
        result = SecurityManager.llm_sanitize(html_entities)
        assert "<script>" not in result.lower()
        assert "alert" not in result.lower()

        # Decimal entity encoding
        decimal_entities = "&#60;script&#62;alert(1)&#60;/script&#62;"
        result = SecurityManager.llm_sanitize(decimal_entities)
        assert "<script>" not in result.lower()

        # Hex entity encoding
        hex_entities = "&#x3C;script&#x3E;alert(1)&#x3C;/script&#x3E;"
        result = SecurityManager.llm_sanitize(hex_entities)
        assert "<script>" not in result.lower()

    def test_double_encoding_bypass_blocked(self):
        """
        Test 4: Double encoding bypass attempts should be neutralized.

        Attackers double-encode to bypass filters that only decode once:
        - %253C = % encoded %3C = <
        - %253E = % encoded %3E = >

        These should be detected and fully decoded/sanitized.
        """
        # Double URL encoding: %25 is '%', so %253C becomes %3C which becomes <
        double_encoded = "%253Cscript%253Ealert(1)%253C%2Fscript%253E"
        result = SecurityManager.llm_sanitize(double_encoded)
        assert "<script>" not in result.lower()
        assert "alert" not in result.lower()

        # Triple encoding attempt
        triple_encoded = "%25253Cscript%25253Ealert(1)%25253C%2Fscript%25253E"
        result = SecurityManager.llm_sanitize(triple_encoded)
        assert "<script>" not in result.lower()

        # Mixed single and double encoding
        mixed = "%3Cscript%253Ealert(1)"
        result = SecurityManager.llm_sanitize(mixed)
        assert "<script>" not in result.lower()

    def test_null_byte_injection_blocked(self):
        """
        Test 5: Null byte injection attempts should be neutralized.

        Attackers use null bytes to truncate strings and bypass filters:
        - %00 in URL encoding
        - \\x00 in string literals
        - \\u0000 in unicode escapes

        These should be stripped entirely from the input.
        """
        # Null byte in the middle of a string
        null_byte_middle = "Hello\x00World"
        result = SecurityManager.llm_sanitize(null_byte_middle)
        assert "\x00" not in result
        assert "HelloWorld" in result or result == "Hello World"

        # URL-encoded null byte
        url_null = "Hello%00World"
        result = SecurityManager.llm_sanitize(url_null)
        assert "%00" not in result
        assert "\x00" not in result

        # Unicode escape null byte
        unicode_null = r"Hello\u0000World"
        result = SecurityManager.llm_sanitize(unicode_null)
        assert "\\u0000" not in result
        assert "\x00" not in result
        assert "\u0000" not in result

        # Hex escape null byte
        hex_null = r"Hello\x00World"
        result = SecurityManager.llm_sanitize(hex_null)
        assert "\\x00" not in result
        assert "\x00" not in result

        # Null byte before malicious content (truncation attack)
        truncation_attack = "\x00<script>alert(1)</script>"
        result = SecurityManager.llm_sanitize(truncation_attack)
        assert "\x00" not in result
        assert "<script>" not in result.lower()

    def test_combined_encoding_attacks_blocked(self):
        """
        Bonus test: Combined encoding attacks should be handled.

        Real-world attacks often combine multiple encoding techniques.
        """
        # URL encoding + HTML entities
        combined1 = "%3C%26lt%3Bscript%26gt%3B%3E"
        result = SecurityManager.llm_sanitize(combined1)
        assert "<script>" not in result.lower()

        # Unicode escape + null byte
        combined2 = r"\u003cscript\u0000>alert(1)"
        result = SecurityManager.llm_sanitize(combined2)
        assert "\x00" not in result
        assert "<script>" not in result.lower()

    def test_legitimate_unicode_content_preserved(self):
        """
        Verify that legitimate unicode content is preserved.

        Sanitization should not destroy valid international characters.
        """
        # International names should be preserved
        international = "José María 日本語"
        result = SecurityManager.llm_sanitize(international)
        assert "José" in result or "Jos" in result  # May be truncated but not mangled

        # Emoji should be handled gracefully (removed or preserved, not crashed)
        emoji_text = "Hello 😀 World"
        result = SecurityManager.llm_sanitize(emoji_text)
        # Should not crash and should preserve some form of the text
        assert "Hello" in result
        assert "World" in result


class TestInputSanitizationIntegration:
    """Integration tests for the sanitize_input method with encoding bypasses."""

    def test_sanitize_input_blocks_encoded_html(self):
        """The basic sanitize_input should also handle encoded HTML."""
        # URL-encoded HTML
        encoded = "%3Cscript%3Ealert(1)%3C/script%3E"
        result = SecurityManager.sanitize_input(encoded)
        assert "<script>" not in result.lower()

        # HTML entities
        entities = "&lt;script&gt;alert(1)&lt;/script&gt;"
        result = SecurityManager.sanitize_input(entities)
        assert "<script>" not in result.lower()

    def test_sanitize_input_strips_null_bytes(self):
        """Null bytes should be stripped by sanitize_input."""
        text = "Hello\x00World"
        result = SecurityManager.sanitize_input(text)
        assert "\x00" not in result

    def test_sanitize_input_strips_newlines(self):
        """Newlines should be stripped by sanitize_input."""
        text = "Line1\nLine2\r\nLine3"
        result = SecurityManager.sanitize_input(text)
        assert "\n" not in result
        assert "\r" not in result
