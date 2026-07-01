import io
import numpy as np
from PIL import Image

SUPPORTED_FORMATS = {"PNG", "BMP"}


def load_image(path: str) -> np.ndarray:
    img = Image.open(path)
    _validate_format(img.format)
    return _to_rgb_array(img)


def load_from_bytes(data: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(data))
    _validate_format(img.format)
    return _to_rgb_array(img)


def to_png_bytes(array: np.ndarray) -> bytes:
    img = Image.fromarray(array.astype(np.uint8), "RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def save_image(array: np.ndarray, path: str) -> None:
    Image.fromarray(array.astype(np.uint8), "RGB").save(path)


def _validate_format(fmt: str | None) -> None:
    if fmt is None or fmt.upper() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format '{fmt}'. Only PNG and BMP are supported "
            "(JPEG is lossy and destroys LSB bits)."
        )


def _to_rgb_array(img: Image.Image) -> np.ndarray:
    return np.array(img.convert("RGB"), dtype=np.uint8)
