import numpy as np


def get_sequential_indices(pixel_array: np.ndarray) -> np.ndarray:
    h, w, _ = pixel_array.shape
    return np.arange(h * w * 3, dtype=np.int64)


def get_scattered_indices(pixel_array: np.ndarray, seed: int) -> np.ndarray:
    h, w, _ = pixel_array.shape
    rng = np.random.default_rng(seed)
    return rng.permutation(h * w * 3).astype(np.int64)


def embed(
    pixel_array: np.ndarray,
    payload_bits: np.ndarray,
    indices: np.ndarray,
) -> np.ndarray:
    stego = pixel_array.copy()
    flat = stego.flatten()
    flat[indices[: len(payload_bits)]] = (
        flat[indices[: len(payload_bits)]] & np.uint8(0xFE)
    ) | payload_bits.astype(np.uint8)
    return flat.reshape(pixel_array.shape)


def extract(
    pixel_array: np.ndarray,
    num_bits: int,
    indices: np.ndarray,
) -> np.ndarray:
    flat = pixel_array.flatten()
    return (flat[indices[:num_bits]] & np.uint8(0x01)).astype(np.uint8)


def bits_to_bytes(bits: np.ndarray) -> bytes:
    n = len(bits) // 8
    result = bytearray(n)
    for i in range(n):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | int(bits[i * 8 + j])
        result[i] = byte
    return bytes(result)


def bytes_to_bits(data: bytes) -> np.ndarray:
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return np.array(bits, dtype=np.uint8)


def calculate_psnr(original: np.ndarray, stego: np.ndarray) -> float:
    mse = float(np.mean((original.astype(np.float64) - stego.astype(np.float64)) ** 2))
    if mse == 0:
        return float("inf")
    return 20 * np.log10(255.0) - 10 * np.log10(mse)


def capacity_bytes(pixel_array: np.ndarray) -> int:
    h, w, c = pixel_array.shape
    return (h * w * c) // 8


# ── Audio LSB (16-bit PCM samples) ────────────────────────────────────────

def audio_capacity_bytes(samples: np.ndarray) -> int:
    """Max payload bytes embeddable via 1-bit-per-sample LSB."""
    return samples.size // 8


def audio_get_sequential_indices(samples: np.ndarray) -> np.ndarray:
    return np.arange(samples.size, dtype=np.int64)


def audio_get_scattered_indices(samples: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.permutation(samples.size).astype(np.int64)


def audio_embed(
    samples: np.ndarray,
    payload_bits: np.ndarray,
    indices: np.ndarray,
) -> np.ndarray:
    """Embed payload_bits into LSB of 16-bit PCM samples."""
    flat = samples.flatten().astype(np.int32)
    n = len(payload_bits)
    flat[indices[:n]] = (flat[indices[:n]] & 0xFFFE) | payload_bits.astype(np.int32)
    return flat.astype(np.int16).reshape(samples.shape)


def audio_extract(
    samples: np.ndarray,
    num_bits: int,
    indices: np.ndarray,
) -> np.ndarray:
    """Extract bits from LSB of 16-bit PCM samples."""
    flat = samples.flatten().astype(np.int32)
    return (flat[indices[:num_bits]] & 1).astype(np.uint8)
