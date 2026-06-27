"""Minimal token generation and validation for stream endpoint security."""

import hashlib
import hmac
import time
import threading


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


class RateLimiter:
    """Thread-safe sliding window rate limiter."""
    def __init__(self, rpm: int = 10):
        self.rpm = rpm
        self.requests = {}  # ip -> list of timestamps
        self.lock = threading.Lock()

    def check(self, ip: str) -> bool:
        """Returns True if the request is allowed, False if rate limited."""
        if self.rpm <= 0:
            return True
            
        now = time.time()
        window_start = now - 60.0

        with self.lock:
            # Clean up old timestamps for this IP
            timestamps = self.requests.get(ip, [])
            timestamps = [ts for ts in timestamps if ts > window_start]
            
            if len(timestamps) >= self.rpm:
                self.requests[ip] = timestamps
                return False
                
            timestamps.append(now)
            self.requests[ip] = timestamps
            
            # Periodically clean up entirely empty IPs to prevent memory leaks
            if len(self.requests) > 1000:
                self.requests = {k: v for k, v in self.requests.items() if any(ts > window_start for ts in v)}

            return True
