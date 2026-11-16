"""Password security, cryptographic token hashing, and authentication rate limiting service.

Task: Secure email-and-password authentication alongside Google OAuth.
Ensures passwords are never stored in plaintext and uses bcrypt with standard cost factor.
Provides rate-limiting to defend against credential stuffing and brute-force attacks.
"""

import hashlib
import re
import secrets
import threading
import time
from typing import Dict, List, Optional, Tuple

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with salt factor 12."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Cryptographically verify a candidate password against an existing bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """Validate password against security complexity policy.

    Rules:
    - Minimum 8 characters
    - Maximum 128 characters (DoS mitigation)
    - At least one letter (a-z, A-Z)
    - At least one number (0-9) or symbol
    """
    if not password:
        return False, "Password cannot be empty."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."
    if not re.search(r"[a-zA-Z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"[\d\W_]", password):
        return False, "Password must contain at least one number or special character."
    return True, None


def generate_raw_token() -> str:
    """Generate a high-entropy URL-safe cryptographic token (256 bits)."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Compute SHA-256 digest of a raw token for secure database storage."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


class AuthRateLimiter:
    """Thread-safe in-memory rate limiter for login and password-reset attempts."""

    def __init__(
        self,
        max_login_failures: int = 5,
        login_lockout_seconds: int = 900,  # 15 minutes
        max_forgot_attempts: int = 3,
        forgot_window_seconds: int = 600,  # 10 minutes
    ):
        self.max_login_failures = max_login_failures
        self.login_lockout_seconds = login_lockout_seconds
        self.max_forgot_attempts = max_forgot_attempts
        self.forgot_window_seconds = forgot_window_seconds
        self._lock = threading.Lock()
        self._login_failures: Dict[str, List[float]] = {}
        self._forgot_requests: Dict[str, List[float]] = {}

    def check_login_rate_limit(self, identifier: str) -> Tuple[bool, int]:
        """Check if an email or IP address is currently locked out from login.

        Returns (is_locked, retry_after_seconds).
        """
        key = identifier.strip().lower()
        now = time.time()
        with self._lock:
            attempts = self._login_failures.get(key, [])
            # Evict attempts older than lockout window
            valid_attempts = [t for t in attempts if now - t < self.login_lockout_seconds]
            self._login_failures[key] = valid_attempts

            if len(valid_attempts) >= self.max_login_failures:
                oldest_in_window = valid_attempts[0]
                retry_after = max(1, int(self.login_lockout_seconds - (now - oldest_in_window)))
                return True, retry_after
            return False, 0

    def record_login_failure(self, identifier: str) -> None:
        """Record an authentication failure for rate limiting."""
        key = identifier.strip().lower()
        now = time.time()
        with self._lock:
            attempts = self._login_failures.get(key, [])
            attempts.append(now)
            self._login_failures[key] = attempts

    def reset_login_failures(self, identifier: str) -> None:
        """Reset failed login count upon successful authentication."""
        key = identifier.strip().lower()
        with self._lock:
            self._login_failures.pop(key, None)

    def check_and_record_forgot_request(self, identifier: str) -> Tuple[bool, int]:
        """Check and record a password reset request.

        Returns (is_limited, retry_after_seconds).
        """
        key = identifier.strip().lower()
        now = time.time()
        with self._lock:
            requests = self._forgot_requests.get(key, [])
            valid_requests = [t for t in requests if now - t < self.forgot_window_seconds]

            if len(valid_requests) >= self.max_forgot_attempts:
                oldest = valid_requests[0]
                retry_after = max(1, int(self.forgot_window_seconds - (now - oldest)))
                self._forgot_requests[key] = valid_requests
                return True, retry_after

            valid_requests.append(now)
            self._forgot_requests[key] = valid_requests
            return False, 0

    def clear(self) -> None:
        """Clear all rate limit buckets (useful for test resets)."""
        with self._lock:
            self._login_failures.clear()
            self._forgot_requests.clear()


auth_rate_limiter = AuthRateLimiter()
