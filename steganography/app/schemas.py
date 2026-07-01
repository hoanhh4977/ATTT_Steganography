from pydantic import BaseModel


class EmbedResponse(BaseModel):
    success: bool
    stego_image: str | None = None     # base64 data URL
    psnr: float | None = None
    capacity_used_pct: float | None = None
    message_bytes: int | None = None
    error: str | None = None


class ExtractResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None


class AnalyzeResponse(BaseModel):
    success: bool
    chi2_score: float | None = None
    p_value: float | None = None
    rs_rate: float | None = None       # RS estimated embedding rate 0..1
    spa_rate: float | None = None      # SPA estimated embedding rate 0..1
    verdict: str | None = None         # "DETECTED" | "CLEAN" | "INCONCLUSIVE"
    threshold: float | None = None
    chart: str | None = None
    error: str | None = None


class AudioEmbedResponse(BaseModel):
    success: bool
    stego_audio: str | None = None     # data:audio/wav;base64,...
    capacity_used_pct: float | None = None
    message_bytes: int | None = None
    sample_rate: int | None = None
    num_samples: int | None = None
    error: str | None = None


class AudioExtractResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None
