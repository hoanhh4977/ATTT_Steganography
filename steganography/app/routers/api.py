import base64
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.core import image_io, crypto, lsb_core, steganalysis
from app.schemas import EmbedResponse, ExtractResponse, AnalyzeResponse

router = APIRouter(prefix="/api")


@router.post("/embed", response_model=EmbedResponse)
async def embed(
    image: UploadFile = File(...),
    message: str = Form(...),
    password: str = Form(...),
    mode: str = Form("sequential"),
):
    try:
        raw = await image.read()
        cover = image_io.load_from_bytes(raw)
    except ValueError as e:
        return EmbedResponse(success=False, error=str(e))

    aes_key, prng_seed = crypto.derive_key_and_seed(password)
    payload = crypto.encrypt(message, aes_key)
    payload_bits = lsb_core.bytes_to_bits(payload)

    cap = lsb_core.capacity_bytes(cover)
    if len(payload) > cap:
        return EmbedResponse(
            success=False,
            error=f"Message too large. Max capacity: {cap} bytes, payload: {len(payload)} bytes.",
        )

    indices = (
        lsb_core.get_scattered_indices(cover, prng_seed)
        if mode == "scattered"
        else lsb_core.get_sequential_indices(cover)
    )

    stego = lsb_core.embed(cover, payload_bits, indices)
    psnr = lsb_core.calculate_psnr(cover, stego)
    used_pct = round(len(payload) / cap * 100, 4)

    png_bytes = image_io.to_png_bytes(stego)
    b64 = "data:image/png;base64," + base64.b64encode(png_bytes).decode()

    return EmbedResponse(
        success=True,
        stego_image=b64,
        psnr=round(psnr, 2),
        capacity_used_pct=used_pct,
        message_bytes=len(message.encode("utf-8")),
    )


@router.post("/extract", response_model=ExtractResponse)
async def extract(
    image: UploadFile = File(...),
    password: str = Form(...),
    mode: str = Form("sequential"),
):
    try:
        raw = await image.read()
        stego = image_io.load_from_bytes(raw)
    except ValueError as e:
        return ExtractResponse(success=False, error=str(e))

    aes_key, prng_seed = crypto.derive_key_and_seed(password)
    indices = (
        lsb_core.get_scattered_indices(stego, prng_seed)
        if mode == "scattered"
        else lsb_core.get_sequential_indices(stego)
    )

    # Read header: IV(128 bits) + length(32 bits) = 160 bits
    header_bits = lsb_core.extract(stego, 160, indices)
    header_bytes = lsb_core.bits_to_bytes(header_bits)
    import struct
    length = struct.unpack(">I", header_bytes[16:20])[0]

    total_payload_bits = (20 + length) * 8
    if total_payload_bits > len(indices):
        return ExtractResponse(success=False, error="No valid payload found in image.")

    payload_bits = lsb_core.extract(stego, total_payload_bits, indices)
    payload = lsb_core.bits_to_bytes(payload_bits)

    try:
        message = crypto.decrypt(payload, aes_key)
    except ValueError as e:
        return ExtractResponse(success=False, error=str(e))

    return ExtractResponse(success=True, message=message)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    image: UploadFile = File(...),
    threshold: float = Form(0.15),   # RS embedding rate threshold (0..1)
):
    try:
        raw = await image.read()
        arr = image_io.load_from_bytes(raw)
    except ValueError as e:
        return AnalyzeResponse(success=False, error=str(e))

    result = steganalysis.chi_squared_test(arr, threshold)
    chart_bytes = steganalysis.generate_chart(arr, f"Chi-squared Analysis — {result.verdict}")
    b64_chart = "data:image/png;base64," + base64.b64encode(chart_bytes).decode()

    return AnalyzeResponse(
        success=True,
        chi2_score=result.chi2_score,
        p_value=result.p_value,
        rs_rate=result.rs_rate,
        spa_rate=result.spa_rate,
        verdict=result.verdict,
        threshold=result.threshold,
        chart=b64_chart,
    )
