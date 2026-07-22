import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config.settings import settings

logger = logging.getLogger(__name__)


class FernetEncryption:
    """Fernet symmetric encryption for sensitive data at rest (DigiLocker tokens, etc.)."""

    def __init__(self, key: Optional[str] = None):
        if key:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        else:
            generated_key = Fernet.generate_key()
            logger.warning(
                "FERNET_ENCRYPTION_KEY not configured. Generated a transient key. "
                "Encrypted data will NOT survive application restarts. "
                "Set FERNET_ENCRYPTION_KEY in your .env for production use."
            )
            self._fernet = Fernet(generated_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string and return base64-encoded ciphertext."""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext and return the original plaintext."""
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            logger.error("Failed to decrypt value — invalid token or wrong encryption key.")
            raise ValueError("Decryption failed: invalid token or encryption key mismatch.")

    def encrypt_or_none(self, value: Optional[str]) -> Optional[str]:
        """Encrypt a value if not None, otherwise return None."""
        if value is None:
            return None
        return self.encrypt(value)

    def decrypt_or_none(self, value: Optional[str]) -> Optional[str]:
        """Decrypt a value if not None, otherwise return None."""
        if value is None:
            return None
        return self.decrypt(value)


# Module-level singleton
fernet_encryption = FernetEncryption(key=settings.FERNET_ENCRYPTION_KEY)
