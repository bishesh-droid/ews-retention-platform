"""
Request signing utilities for integration API authentication.
Uses HMAC-SHA256 with timestamp-based replay protection.
"""

import hmac
import time

from backend.config import INTEGRATION_API_KEY_HASH

SIGNATURE_WINDOW_SECONDS = 300  # 5-minute replay window


def verify_signed_request(
    api_key_hash_from_header: str,
    timestamp_header: str,
) -> bool:
    """
    Verifies signed request with timestamp-based replay protection.

    Client must send:
      X-API-Key-Hash: sha256(raw_api_key)
      X-Timestamp: unix_timestamp_string

    Server verifies:
      1. Timestamp is within window (prevents replay attacks)
      2. Key hash matches stored hash (constant-time comparison)
    """
    # 1. Verify timestamp is within window (prevents replay attacks)
    try:
        req_time = int(timestamp_header)
    except (ValueError, TypeError):
        return False

    if abs(time.time() - req_time) > SIGNATURE_WINDOW_SECONDS:
        return False

    # 2. Verify the key hash matches stored hash (constant-time comparison)
    if not hmac.compare_digest(
        api_key_hash_from_header.encode(), INTEGRATION_API_KEY_HASH.encode()
    ):
        return False

    return True


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())
