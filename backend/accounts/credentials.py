from django.conf import settings
import base64
import hashlib


def _cipher():
    from cryptography.fernet import Fernet

    key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt_password(password: str) -> str:
    return _cipher().encrypt(password.encode()).decode()


def decrypt_password(value: str) -> str:
    return _cipher().decrypt(value.encode()).decode()
