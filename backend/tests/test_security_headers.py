"""
Security Headers Tests
---------------------
Tests that verify security headers are present on all HTTP responses.

These tests ensure protection against:
- XSS attacks
- Clickjacking
- MIME sniffing
- Protocol downgrade attacks
- Referrer leakage
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


class TestSecurityHeaders:
    """Tests for security headers on HTTP responses."""

    def test_all_security_headers_present_on_root(self):
        """
        Test that all 6 required security headers are present on 200 response.
        
        Headers verified:
        1. Strict-Transport-Security (HSTS)
        2. X-Content-Type-Options
        3. X-Frame-Options
        4. X-XSS-Protection
        5. Content-Security-Policy
        6. Referrer-Policy
        """
        response = client.get("/")
        
        assert response.status_code == 200
        
        # 1. Strict-Transport-Security (HSTS)
        hsts = response.headers.get("Strict-Transport-Security")
        assert hsts is not None, "Missing Strict-Transport-Security header"
        assert "max-age=31536000" in hsts, "HSTS max-age should be 1 year"
        assert "includeSubDomains" in hsts, "HSTS should include subdomains"
        
        # 2. X-Content-Type-Options (MIME sniffing protection)
        content_type_options = response.headers.get("X-Content-Type-Options")
        assert content_type_options == "nosniff", "X-Content-Type-Options should be 'nosniff'"
        
        # 3. X-Frame-Options (clickjacking protection)
        frame_options = response.headers.get("X-Frame-Options")
        assert frame_options == "DENY", "X-Frame-Options should be 'DENY'"
        
        # 4. X-XSS-Protection (legacy XSS protection)
        xss_protection = response.headers.get("X-XSS-Protection")
        assert xss_protection == "1; mode=block", "X-XSS-Protection should be '1; mode=block'"
        
        # 5. Content-Security-Policy
        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None, "Missing Content-Security-Policy header"
        assert "default-src 'self'" in csp, "CSP should have default-src 'self'"
        assert "frame-ancestors 'none'" in csp, "CSP should prevent framing"
        
        # 6. Referrer-Policy
        referrer_policy = response.headers.get("Referrer-Policy")
        assert referrer_policy == "strict-origin-when-cross-origin", \
            "Referrer-Policy should be 'strict-origin-when-cross-origin'"

    def test_security_headers_on_api_endpoint(self):
        """Verify headers are present on API endpoints."""
        response = client.get("/api/v1/students")
        
        # Even if endpoint returns 401/403, headers should be present
        assert "Strict-Transport-Security" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers

    def test_hsts_header_format(self):
        """Verify HSTS header has correct format and values."""
        response = client.get("/")
        hsts = response.headers.get("Strict-Transport-Security")
        
        # Should contain max-age of 31536000 seconds (1 year)
        assert "max-age=31536000" in hsts
        
        # Should include subdomains
        assert "includeSubDomains" in hsts

    def test_csp_includes_react_exceptions(self):
        """
        Verify CSP allows necessary resources for React SPA.
        
        React requires:
        - 'unsafe-inline' for styles (CSS-in-JS, styled-components)
        - data: and blob: URIs for images
        """
        response = client.get("/")
        csp = response.headers.get("Content-Security-Policy")
        
        # React-friendly exceptions
        assert "'unsafe-inline'" in csp, "CSP should allow inline styles for React"
        assert "data:" in csp, "CSP should allow data URIs for images"
        assert "blob:" in csp, "CSP should allow blob URIs for images"

    def test_no_caching_headers_present(self):
        """Verify cache-control headers are set to prevent sensitive data caching."""
        response = client.get("/")
        
        cache_control = response.headers.get("Cache-Control")
        assert cache_control is not None
        assert "no-store" in cache_control or "max-age=0" in cache_control

    def test_headers_on_error_response(self):
        """Verify security headers are present even on error responses."""
        # Hit a non-existent endpoint to trigger 404
        response = client.get("/nonexistent-endpoint")
        
        # Headers should still be present on 404
        assert "Strict-Transport-Security" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers
