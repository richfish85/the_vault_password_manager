import base64
import hashlib
import hmac
import os

import pyaes

from app.core.config import get_settings

settings = get_settings()


def _keys() -> tuple[bytes, bytes]:
    secret = settings.encryption_key.encode("utf-8")
    encryption_key = hashlib.sha256(b"enc:" + secret).digest()
    signing_key = hashlib.sha256(b"sig:" + secret).digest()
    return encryption_key, signing_key


def _counter(nonce: bytes) -> pyaes.Counter:
    return pyaes.Counter(initial_value=int.from_bytes(nonce, "big"))


def encrypt_value(plaintext: str) -> tuple[str, str]:
    nonce = os.urandom(16)
    encryption_key, signing_key = _keys()
    aes = pyaes.AESModeOfOperationCTR(encryption_key, counter=_counter(nonce))
    ciphertext = aes.encrypt(plaintext.encode("utf-8"))
    signature = hmac.new(signing_key, nonce + ciphertext, hashlib.sha256).digest()
    return (
        base64.urlsafe_b64encode(ciphertext + signature).decode("utf-8"),
        base64.urlsafe_b64encode(nonce).decode("utf-8"),
    )


def decrypt_value(ciphertext: str, nonce: str) -> str:
    raw_payload = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
    raw_nonce = base64.urlsafe_b64decode(nonce.encode("utf-8"))
    raw_ciphertext = raw_payload[:-32]
    signature = raw_payload[-32:]
    encryption_key, signing_key = _keys()
    expected_signature = hmac.new(signing_key, raw_nonce + raw_ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Ciphertext integrity check failed.")
    aes = pyaes.AESModeOfOperationCTR(encryption_key, counter=_counter(raw_nonce))
    plaintext = aes.decrypt(raw_ciphertext)
    return plaintext.decode("utf-8")
