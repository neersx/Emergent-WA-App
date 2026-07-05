"""Symmetric envelope encryption for at-rest secrets (Meta business tokens)."""
from cryptography.fernet import Fernet
from .config import settings

_fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()
