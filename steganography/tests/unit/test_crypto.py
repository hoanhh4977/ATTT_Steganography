import struct
import pytest
from app.core.crypto import derive_key_and_seed, encrypt, decrypt


def test_derive_returns_16_byte_key():
    key, seed = derive_key_and_seed("password")
    assert len(key) == 16
    assert isinstance(seed, int)


def test_derive_deterministic():
    k1, s1 = derive_key_and_seed("hello")
    k2, s2 = derive_key_and_seed("hello")
    assert k1 == k2 and s1 == s2


def test_derive_different_passwords():
    k1, _ = derive_key_and_seed("pass1")
    k2, _ = derive_key_and_seed("pass2")
    assert k1 != k2


def test_encrypt_payload_format():
    key, _ = derive_key_and_seed("test")
    payload = encrypt("hello", key)
    iv = payload[:16]
    length = struct.unpack(">I", payload[16:20])[0]
    ciphertext = payload[20:]
    assert len(iv) == 16
    assert len(ciphertext) == length
    assert length % 16 == 0  # AES block size


def test_encrypt_nondeterministic():
    key, _ = derive_key_and_seed("test")
    p1 = encrypt("hello", key)
    p2 = encrypt("hello", key)
    assert p1 != p2  # different IV each time


def test_roundtrip():
    key, _ = derive_key_and_seed("mypassword")
    original = "Secret message 🔐"
    payload = encrypt(original, key)
    result = decrypt(payload, key)
    assert result == original


def test_wrong_key_raises():
    key1, _ = derive_key_and_seed("correct")
    key2, _ = derive_key_and_seed("wrong")
    payload = encrypt("secret", key1)
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt(payload, key2)


def test_short_payload_raises():
    key, _ = derive_key_and_seed("test")
    with pytest.raises(ValueError):
        decrypt(b"\x00" * 10, key)
