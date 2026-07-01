import io
import numpy as np
import scipy.io.wavfile as wavfile


def load_from_bytes(data: bytes) -> tuple[int, np.ndarray]:
    """Read WAV bytes → (sample_rate, int16 mono ndarray)."""
    buf = io.BytesIO(data)
    try:
        rate, samples = wavfile.read(buf)
    except Exception as e:
        raise ValueError(f"Cannot read WAV file: {e}") from e

    if samples.ndim > 1:          # stereo → left channel
        samples = samples[:, 0]

    if samples.dtype in (np.float32, np.float64):
        samples = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    elif samples.dtype == np.int32:
        samples = (samples >> 16).astype(np.int16)
    else:
        samples = samples.astype(np.int16)

    return rate, samples


def to_wav_bytes(rate: int, samples: np.ndarray) -> bytes:
    """int16 ndarray → WAV bytes."""
    buf = io.BytesIO()
    wavfile.write(buf, rate, samples.astype(np.int16))
    return buf.getvalue()
