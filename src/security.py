"""Minimal token generation and validation for stream endpoint security."""

import hashlib
import hmac
import time


def generate_token(query: str, secret: str) -> str:
    """Generate a time-bound HMAC token that includes the query.

    Format: "{timestamp}.{hmac_hex}"
    The HMAC covers both the timestamp and the query, so tokens
    cannot be reused across different queries.
    """
    ts = str(int(time.time()))
    message = f"{ts}:{query}".encode()
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"{ts}.{signature}"


def validate_token(token: str, query: str, secret: str, max_age: int = 3600) -> bool:
    """Validate a token against the query and check expiry.

    Returns True if the token is valid and not expired.
    """
    try:
        ts_str, signature = token.rsplit(".", 1)
        ts = float(ts_str)
    except (ValueError, AttributeError):
        return False

    # Check expiry
    if (time.time() - ts) > max_age:
        return False

    # Recompute HMAC and compare
    message = f"{ts_str}:{query}".encode()
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
