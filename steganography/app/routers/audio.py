import base64
import struct
from fastapi import APIRouter, UploadFile, File, Form

from app.core import audio_io, crypto, lsb_core
from app.schemas import AudioEmbedResponse, AudioExtractResponse

router = APIRouter(prefix="/api/audio")


@router.post("/embed", response_model=AudioEmbedResponse)
async def embed_audio(
    audio: UploadFile = File(...),
    message: str = Form(...),
    password: str = Form(...),
    mode: str = Form("sequential"),
):
    try:
        raw = await audio.read()
        rate, samples = audio_io.load_from_bytes(raw)
    except ValueError as e:
        return AudioEmbedResponse(success=False, error=str(e))

    aes_key, prng_seed = crypto.derive_key_and_seed(password)
    payload = crypto.encrypt(message, aes_key)
    payload_bits = lsb_core.bytes_to_bits(payload)

    cap = lsb_core.audio_capacity_bytes(samples)
    if len(payload) > cap:
        return AudioEmbedResponse(
            success=False,
            error=f"Message too large. Max: {cap} bytes, payload: {len(payload)} bytes.",
        )

    indices = (
        lsb_core.audio_get_scattered_indices(samples, prng_seed)
        if mode == "scattered"
        else lsb_core.audio_get_sequential_indices(samples)
    )

    stego_samples = lsb_core.audio_embed(samples, payload_bits, indices)
    used_pct = round(len(payload) / cap * 100, 4)

    wav_bytes = audio_io.to_wav_bytes(rate, stego_samples)
    b64 = "data:audio/wav;base64," + base64.b64encode(wav_bytes).decode()

    return AudioEmbedResponse(
        success=True,
        stego_audio=b64,
        capacity_used_pct=used_pct,
        message_bytes=len(message.encode("utf-8")),
        sample_rate=rate,
        num_samples=int(samples.size),
    )


@router.post("/extract", response_model=AudioExtractResponse)
async def extract_audio(
    audio: UploadFile = File(...),
    password: str = Form(...),
    mode: str = Form("sequential"),
):
    try:
        raw = await audio.read()
        rate, samples = audio_io.load_from_bytes(raw)
    except ValueError as e:
        return AudioExtractResponse(success=False, error=str(e))

    aes_key, prng_seed = crypto.derive_key_and_seed(password)
    indices = (
        lsb_core.audio_get_scattered_indices(samples, prng_seed)
        if mode == "scattered"
        else lsb_core.audio_get_sequential_indices(samples)
    )

    # Header: IV (16 bytes) + length (4 bytes) = 160 bits
    header_bits = lsb_core.audio_extract(samples, 160, indices)
    header_bytes = lsb_core.bits_to_bytes(header_bits)
    length = struct.unpack(">I", header_bytes[16:20])[0]

    total_bits = (20 + length) * 8
    if total_bits > samples.size:
        return AudioExtractResponse(success=False, error="No valid payload found in audio.")

    payload_bits = lsb_core.audio_extract(samples, total_bits, indices)
    payload = lsb_core.bits_to_bytes(payload_bits)

    try:
        message = crypto.decrypt(payload, aes_key)
    except ValueError as e:
        return AudioExtractResponse(success=False, error=str(e))

    return AudioExtractResponse(success=True, message=message)
