import numpy as np
from PIL import Image

from app.core import steganalysis


def _natural_like_image(h=256, w=256, seed=42) -> np.ndarray:
    """Tạo ảnh có tương quan không gian (giống ảnh tự nhiên) bằng cách
    upsample một mảng nhiễu nhỏ qua bilinear resize — RS/SPA đều giả định
    pixel liền kề có độ trơn (smoothness), khác với nhiễu ngẫu nhiên thuần."""
    rng = np.random.default_rng(seed)
    small = rng.integers(0, 256, (h // 16, w // 16, 3), dtype=np.uint8)
    img = Image.fromarray(small, "RGB").resize((w, h), Image.BILINEAR)
    return np.array(img, dtype=np.uint8)


def _embed_random_lsb(pixel_array: np.ndarray, fraction: float, seed=7) -> np.ndarray:
    """Ghi đè LSB của R channel tại `fraction` tỉ lệ pixel bằng bit ngẫu nhiên —
    mô phỏng trực tiếp embedding rate p, độc lập với lsb_core/capacity semantics."""
    rng = np.random.default_rng(seed)
    stego = pixel_array.copy()
    r = stego[:, :, 0].flatten()
    n = r.size
    n_embed = int(n * fraction)
    idx = rng.choice(n, size=n_embed, replace=False)
    random_bits = rng.integers(0, 2, size=n_embed, dtype=np.uint8)
    r[idx] = (r[idx] & 0xFE) | random_bits
    stego[:, :, 0] = r.reshape(stego[:, :, 0].shape)
    return stego


def test_clean_image_low_rates():
    cover = _natural_like_image()
    result = steganalysis.chi_squared_test(cover, threshold=0.15)
    assert result.rs_rate < 0.1
    assert result.spa_rate < 0.1
    assert result.verdict == "CLEAN"


def test_heavy_embedding_detected_by_both():
    cover = _natural_like_image()
    stego = _embed_random_lsb(cover, fraction=0.5)
    result = steganalysis.chi_squared_test(stego, threshold=0.15)
    assert result.rs_rate > 0.3
    assert result.spa_rate > 0.3
    assert result.verdict == "DETECTED"


def test_spa_estimate_has_lower_error_than_rs_at_low_rate():
    """SPA ước tính embedding rate chính xác hơn RS (sai số thấp hơn) ở rate
    thấp — đây là lý do giữ spa_rate làm tín hiệu phụ để hiển thị/đối chiếu.
    KHÔNG có nghĩa SPA quyết định verdict (xem research.md R-009: dùng SPA
    cho verdict qua max() đã được thực nghiệm và KHÔNG cải thiện recall,
    chỉ làm tăng false positive vì RS bias lại "tình cờ" giúp nó vượt
    threshold đúng lúc cần — verdict vẫn dựa trên rs_rate)."""
    cover = _natural_like_image()
    true_p = 0.05
    stego = _embed_random_lsb(cover, fraction=true_p)
    result = steganalysis.chi_squared_test(stego, threshold=0.15)
    assert abs(result.spa_rate - true_p) <= abs(result.rs_rate - true_p) + 0.02


def test_verdict_uses_rs_rate_not_max_with_spa():
    """Verdict phải dựa trên rs_rate đơn thuần — không phải max(rs_rate, spa_rate).
    Regression cho quyết định thiết kế trong research.md R-009."""
    cover = _natural_like_image()
    stego = _embed_random_lsb(cover, fraction=0.5)
    result = steganalysis.chi_squared_test(stego, threshold=0.15)
    expected_verdict = "DETECTED" if result.rs_rate > 0.15 else "CLEAN"
    assert result.verdict == expected_verdict


def test_inconclusive_on_tiny_image():
    tiny = np.zeros((1, 1, 3), dtype=np.uint8)
    result = steganalysis.chi_squared_test(tiny, threshold=0.15)
    assert result.spa_rate == -1.0


def test_sample_pair_analysis_standalone():
    cover = _natural_like_image()
    p = steganalysis.sample_pair_analysis(cover)
    assert 0.0 <= p < 0.1


def _multi_octave_image(h=512, w=512, seed=7) -> np.ndarray:
    """Texture đa tầng (nhiều octave noise resize) — dùng để tái lập bug
    discriminant âm trong rs_analysis (xem research.md R-009)."""
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), dtype=np.float64)
    for octave_size in (4, 8, 16, 32, 64):
        small = rng.integers(0, 256, (octave_size, octave_size, 3), dtype=np.uint8)
        layer = np.array(
            Image.fromarray(small, "RGB").resize((w, h), Image.BICUBIC), dtype=np.float64
        )
        img += layer / 5
    return np.clip(img, 0, 255).astype(np.uint8)


def test_rs_negative_discriminant_does_not_blow_up():
    """Regression: ảnh sạch (seed=7, 512x512) từng trả rs_rate≈0.9444 do
    nhánh xấp xỉ Taylor chia hai số rất nhỏ cho nhau khi discriminant âm.
    Bây giờ phải trả 0.0 (không detect) cho trường hợp này."""
    cover = _multi_octave_image(512, 512, seed=7)
    p = steganalysis.rs_analysis(cover)
    assert p < 0.15
