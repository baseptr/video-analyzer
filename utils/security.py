"""
Security utilities for encryption and rate limiting.
"""

import os
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# Encryption for sensitive data
# ============================================================================

try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    logger.warning("cryptography not installed. Install with: pip install cryptography")
    ENCRYPTION_AVAILABLE = False


class EncryptionService:
    """Service for encrypting/decrypting sensitive data."""

    def __init__(self):
        self.cipher = None
        self._init_cipher()

    def _init_cipher(self):
        """Initialize encryption cipher."""
        if not ENCRYPTION_AVAILABLE:
            return

        # Get encryption key from environment
        encryption_key = os.getenv("ENCRYPTION_KEY")

        if not encryption_key:
            logger.warning(
                "ENCRYPTION_KEY not set. Generate one with:\n"
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
            return

        try:
            self.cipher = Fernet(encryption_key.encode())
            logger.info("Encryption service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")

    def encrypt(self, plaintext: str) -> Optional[str]:
        """Encrypt plaintext string."""
        if not self.cipher:
            logger.warning("Encryption not available - storing plaintext")
            return plaintext

        try:
            encrypted = self.cipher.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return None

    def decrypt(self, ciphertext: str) -> Optional[str]:
        """Decrypt encrypted string."""
        if not self.cipher:
            return ciphertext

        try:
            decrypted = self.cipher.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.debug(f"Decryption error (might be plaintext): {e}")
            return ciphertext


# Global encryption service
_encryption_service = None


def get_encryption() -> EncryptionService:
    """Get global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# ============================================================================
# Rate Limiting
# ============================================================================

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    logger.warning("slowapi not installed. Install with: pip install slowapi")
    RATE_LIMIT_AVAILABLE = False


def get_rate_limiter():
    """Create rate limiter instance."""
    if not RATE_LIMIT_AVAILABLE:
        logger.warning("Rate limiting not available")
        return None

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["100 per hour"],
        storage_uri=os.getenv("REDIS_URL", "memory://"),
    )

    return limiter


# Rate limit configurations
RATE_LIMITS = {
    "upload": "50 per hour",
    "analyze": "100 per hour",
    "api": "200 per hour",
}


def get_rate_limit(endpoint_type: str) -> str:
    """Get rate limit for endpoint type."""
    return RATE_LIMITS.get(endpoint_type, "100 per hour")


# ============================================================================
# CORS Configuration
# ============================================================================

def get_cors_origins() -> list:
    """Get allowed CORS origins from environment."""
    origins_str = os.getenv("ALLOWED_ORIGINS", "")

    if not origins_str:
        logger.warning("ALLOWED_ORIGINS not set. Using development defaults.")
        return [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:8000",
        ]

    origins = [origin.strip() for origin in origins_str.split(",")]

    if "*" in origins:
        logger.warning("CORS wildcard (*) is enabled. Not recommended for production!")

    return origins


# ============================================================================
# Security Headers
# ============================================================================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def get_security_headers() -> dict:
    """Get recommended security headers."""
    return SECURITY_HEADERS.copy()
