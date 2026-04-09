"""
Security Headers Middleware
----------------------------
Adds security headers to all HTTP responses for protection against
common web vulnerabilities (XSS, clickjacking, MIME sniffing, etc.).

Headers added:
- Strict-Transport-Security (HSTS): Enforces HTTPS
- X-Content-Type-Options: Prevents MIME sniffing
- X-Frame-Options: Prevents clickjacking
- X-XSS-Protection: Legacy XSS protection for older browsers
- Content-Security-Policy: Restricts resource loading
- Referrer-Policy: Controls referrer information leakage
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to every HTTP response.
    
    These headers protect against:
    - XSS attacks (X-XSS-Protection, CSP)
    - Clickjacking (X-Frame-Options)
    - MIME sniffing (X-Content-Type-Options)
    - Protocol downgrade attacks (HSTS)
    - Referrer leakage (Referrer-Policy)
    """

    # CSP policy optimized for React SPA with API backend
    # - default-src 'self': Only allow resources from same origin by default
    # - connect-src: Allow API calls to same origin
    # - script-src 'self': Only allow scripts from same origin
    # - style-src 'self' 'unsafe-inline': Allow inline styles (needed for React/CSS-in-JS)
    # - img-src 'self' data: blob:: Allow images from same origin, data URIs, and blobs
    # - font-src 'self': Only allow fonts from same origin
    CONTENT_SECURITY_POLICY = (
        "default-src 'self'; "
        "connect-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Add security headers to every response."""
        response = await call_next(request)

        # HTTP Strict Transport Security (HSTS)
        # Enforces HTTPS for 1 year, includes subdomains
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking by disallowing framing
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.CONTENT_SECURITY_POLICY

        # Referrer Policy: only send origin when cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Additional security headers (best practice)
        # Disable caching of sensitive data by default
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"

        return response
