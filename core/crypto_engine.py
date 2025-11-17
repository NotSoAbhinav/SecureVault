from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64

class CryptoEngine:
    def __init__(self, iterations=200000):
        self.iterations = iterations

    def derive_key(self, password, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.iterations,
        )
        return kdf.derive(password)

    def encrypt_bytes(self, plaintext_bytes, password_bytes):
        salt = os.urandom(16)
        key = self.derive_key(password_bytes, salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext_bytes, None)
        # store salt & nonce as bytes in DB (BLOB)
        return salt, nonce, ct

    def decrypt_bytes(self, ciphertext_bytes, password_bytes, salt, nonce):
        key = self.derive_key(password_bytes, salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext_bytes, None)
