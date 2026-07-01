import os
import struct
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

_SALT = b"stego_salt_2025"
_ITERATIONS = 100_000
_DKLEN = 32


def derive_key_and_seed(password: str) -> tuple[bytes, int]:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        _SALT,
        _ITERATIONS,
        dklen=_DKLEN,
    )
    aes_key = derived[:16]
    prng_seed = int.from_bytes(derived[16:24], "big")
    return aes_key, prng_seed


def encrypt(plaintext: str, aes_key: bytes) -> bytes:
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    enc = cipher.encryptor()
    ciphertext = enc.update(padded) + enc.finalize()
    length = struct.pack(">I", len(ciphertext))
    return iv + length + ciphertext


def decrypt(payload: bytes, aes_key: bytes) -> str:
    if len(payload) < 20:
        raise ValueError("Payload too short — no valid data found.")
    iv = payload[:16]
    length = struct.unpack(">I", payload[16:20])[0]
    ciphertext = payload[20 : 20 + length]
    if len(ciphertext) != length:
        raise ValueError("Payload corrupted — length mismatch.")
    try:
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        dec = cipher.decryptor()
        padded = dec.update(ciphertext) + dec.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()
        return plaintext.decode("utf-8")
    except Exception:
        raise ValueError("Decryption failed. Wrong password or image not stego.")
