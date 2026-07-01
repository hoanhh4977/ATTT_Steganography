import io
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_png(w=64, h=64) -> bytes:
    arr = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
    img = Image.fromarray(arr, "RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_embed_returns_200():
    png = _make_png()
    res = client.post(
        "/api/embed",
        data={"message": "hello test", "password": "secret", "mode": "sequential"},
        files={"image": ("test.png", png, "image/png")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["stego_image"].startswith("data:image/png;base64,")
    assert body["psnr"] >= 40.0


def test_roundtrip_sequential():
    png = _make_png(128, 128)
    msg = "Secret roundtrip message 🔐"

    embed_res = client.post(
        "/api/embed",
        data={"message": msg, "password": "pass123", "mode": "sequential"},
        files={"image": ("cover.png", png, "image/png")},
    ).json()
    assert embed_res["success"]

    import base64
    stego_bytes = base64.b64decode(embed_res["stego_image"].split(",")[1])

    extract_res = client.post(
        "/api/extract",
        data={"password": "pass123", "mode": "sequential"},
        files={"image": ("stego.png", stego_bytes, "image/png")},
    ).json()
    assert extract_res["success"]
    assert extract_res["message"] == msg


def test_wrong_password_fails():
    png = _make_png(64, 64)
    embed_res = client.post(
        "/api/embed",
        data={"message": "secret", "password": "correct", "mode": "sequential"},
        files={"image": ("cover.png", png, "image/png")},
    ).json()
    assert embed_res["success"]

    import base64
    stego_bytes = base64.b64decode(embed_res["stego_image"].split(",")[1])
    extract_res = client.post(
        "/api/extract",
        data={"password": "wrong", "mode": "sequential"},
        files={"image": ("stego.png", stego_bytes, "image/png")},
    ).json()
    assert extract_res["success"] is False
    assert "Decryption failed" in extract_res["error"]


def test_analyze_clean_image():
    png = _make_png(128, 128)
    res = client.post(
        "/api/analyze",
        data={"threshold": "50"},
        files={"image": ("clean.png", png, "image/png")},
    ).json()
    assert res["success"]
    assert res["verdict"] in ("CLEAN", "DETECTED")
    assert res["chart"].startswith("data:image/png;base64,")


def test_roundtrip_scattered():
    png = _make_png(128, 128)
    msg = "Scattered mode test"
    embed_res = client.post(
        "/api/embed",
        data={"message": msg, "password": "scatterpass", "mode": "scattered"},
        files={"image": ("cover.png", png, "image/png")},
    ).json()
    assert embed_res["success"]

    import base64
    stego_bytes = base64.b64decode(embed_res["stego_image"].split(",")[1])
    extract_res = client.post(
        "/api/extract",
        data={"password": "scatterpass", "mode": "scattered"},
        files={"image": ("stego.png", stego_bytes, "image/png")},
    ).json()
    assert extract_res["success"]
    assert extract_res["message"] == msg
