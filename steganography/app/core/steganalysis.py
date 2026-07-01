"""
Steganalysis module — ba kỹ thuật detection:

1. RS (Regular-Singular) Analysis (Fridrich et al. 2001) — PRIMARY, quyết
   định verdict:
   Chia ảnh thành nhóm pixel nhỏ, áp mask lật LSB, phân loại nhóm là
   Regular (R), Singular (S) dựa trên hàm smoothness. Từ tỷ lệ R/S ước
   tính embedding rate p. Robust với mọi loại ảnh, image-size independent.

2. SPA (Sample Pair Analysis, Dumitrescu/Wu/Wang 2003) — tín hiệu phụ:
   Phân loại các cặp pixel liền kề (ngang + dọc) thành 4 multiset
   X, Y, W, Z dựa trên quan hệ thứ tự + tính chẵn lẻ. Giải phương trình
   bậc 2 để ước tính embedding rate p. Sai số ước tính thấp hơn RS đáng kể
   (ít bias hơn), NHƯNG vì RS có xu hướng overestimate trên nhiều loại
   ảnh, RS lại thường vượt threshold sớm hơn (nhạy hơn theo nghĩa thực
   dụng dù kém chính xác hơn). Do đó verdict KHÔNG dùng spa_rate — xem
   research.md R-009 phần "Phát hiện qua thực nghiệm" để biết lý do đầy đủ.

3. Chi-squared test (Westfeld & Pfitzmann 1999) — SECONDARY:
   Đo mức độ pair (2k, 2k+1) tiến đến equalization. Bổ sung cho RS/SPA.

Verdict cuối cùng dựa trên rs_rate so với threshold (giữ thiết kế R-008).
spa_rate vẫn trả về để hiển thị/đối chiếu nhưng không ảnh hưởng verdict.
"""

import io
from dataclasses import dataclass, field

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as scipy_stats


@dataclass
class AnalysisResult:
    chi2_score: float
    p_value: float
    rs_rate: float          # RS estimated embedding rate 0..1 (-1 if inconclusive)
    spa_rate: float         # SPA estimated embedding rate 0..1 (-1 if inconclusive)
    verdict: str
    threshold: float
    pair_scores: list[float] = field(default_factory=list)


# ── Smoothness function ────────────────────────────────────────────────────
def _smoothness(group: np.ndarray) -> float:
    return float(np.sum(np.abs(np.diff(group.astype(np.int32)))))


def _apply_mask(group: np.ndarray, mask: np.ndarray, invert: bool = False) -> np.ndarray:
    g = group.copy().astype(np.int32)
    for i, m in enumerate(mask):
        if m == 0:
            continue
        if not invert:
            g[i] = g[i] ^ 1                          # F+1: flip LSB
        else:
            g[i] = g[i] - 1 if g[i] % 2 == 0 else g[i] + 1  # F-1: 2k↔2k-1
    return np.clip(g, 0, 255).astype(np.uint8)


# ── RS Analysis ────────────────────────────────────────────────────────────
def rs_analysis(pixel_array: np.ndarray, group_size: int = 4) -> float:
    """
    Ước tính embedding rate p ∈ [0, 1]. Trả về -1.0 nếu không kết luận được.

    Nguyên lý:
    - Ảnh sạch: R_m >> S_m, R_-m >> S_-m, R_m ≈ R_-m
    - Càng nhúng nhiều: R_m và S_m tiến gần nhau, S_-m tiến về R_-m
    - Giải phương trình bậc 2 để tính p từ R_m, S_m, R_-m, S_-m
    """
    channel = pixel_array[:, :, 0].flatten().astype(np.uint8)
    n = len(channel)
    n_groups = n // group_size
    if n_groups < 10:
        return -1.0

    mask = np.array([0, 1, 1, 0], dtype=np.int32)
    R_m = S_m = R_n = S_n = 0

    for i in range(n_groups):
        g = channel[i * group_size : (i + 1) * group_size]
        f0 = _smoothness(g)

        gm = _apply_mask(g, mask, invert=False)
        fm = _smoothness(gm)
        if fm > f0:
            R_m += 1
        elif fm < f0:
            S_m += 1

        gn = _apply_mask(g, mask, invert=True)
        fn = _smoothness(gn)
        if fn > f0:
            R_n += 1
        elif fn < f0:
            S_n += 1

    total = float(n_groups)
    R_m /= total; S_m /= total; R_n /= total; S_n /= total

    # Quadratic: 2(R_m - S_m)p² + (R_-m - S_-m - R_m + S_m)p + (R_m - R_-m) = 0
    a = 2.0 * (R_m - S_m)
    b = (R_n - S_n) - (R_m - S_m)
    c = R_m - R_n

    if abs(a) < 1e-10:
        p = -c / b if abs(b) > 1e-10 else 0.0
    else:
        disc = b * b - 4 * a * c
        if disc < 0:
            # Negative discriminant chỉ xảy ra khi R_m≈R_-m và S_m≈S_-m (ảnh sạch) —
            # đây là vertex của parabola tại p≈0, không phải lỗi cần "xấp xỉ tuyến tính".
            # (Từng dùng Taylor approx ở đây nhưng chia hai số rất nhỏ cho nhau gây
            # kết quả ảo lên tới p≈0.94 trên ảnh hoàn toàn sạch — đã verify bằng test.)
            return 0.0
        else:
            p1 = (-b + np.sqrt(disc)) / (2 * a)
            p2 = (-b - np.sqrt(disc)) / (2 * a)
            candidates = [x for x in [p1, p2] if -0.1 <= x <= 1.1]
            if not candidates:
                return 0.0
            p = min(candidates, key=lambda x: abs(x - 0.5))

    return float(np.clip(p, 0.0, 1.0))


# ── SPA (Sample Pair Analysis) ─────────────────────────────────────────────
def _classify_pairs(channel: np.ndarray) -> tuple[int, int, int, int, int]:
    """
    Trace multiset = mọi cặp pixel liền kề ngang + dọc (non-overlapping).
    Phân loại theo Dumitrescu/Wu/Wang 2003:
      Z: u == v
      X: (v chẵn và u < v) hoặc (v lẻ và u > v)
      Y: phần còn lại (không Z, không X)
      W: tập con của Y mà floor(u/2) == floor(v/2) (chỉ khác bit LSB)
    """
    h, w = channel.shape
    pairs_u, pairs_v = [], []

    ncols = (w // 2) * 2
    if ncols >= 2:
        pairs_u.append(channel[:, 0:ncols:2].ravel())
        pairs_v.append(channel[:, 1:ncols:2].ravel())

    nrows = (h // 2) * 2
    if nrows >= 2:
        pairs_u.append(channel[0:nrows:2, :].ravel())
        pairs_v.append(channel[1:nrows:2, :].ravel())

    if not pairs_u:
        return 0, 0, 0, 0, 0

    u = np.concatenate(pairs_u).astype(np.int32)
    v = np.concatenate(pairs_v).astype(np.int32)
    P = u.size

    z_mask = u == v
    Z = int(np.sum(z_mask))

    not_z = ~z_mask
    v_even = (v % 2) == 0
    x_mask = not_z & (((v_even) & (u < v)) | (~v_even & (u > v)))
    X = int(np.sum(x_mask))

    y_mask = not_z & ~x_mask
    Y = int(np.sum(y_mask))

    w_mask = y_mask & ((u // 2) == (v // 2))
    W = int(np.sum(w_mask))

    return P, X, Y, W, Z


def sample_pair_analysis(pixel_array: np.ndarray) -> float:
    """
    Ước tính embedding rate p ∈ [0, 1] bằng SPA. Trả về -1.0 nếu không
    đủ dữ liệu để kết luận. Giải phương trình bậc 2:
        0.5*(W+Z)*p² + (2X - P)*p + (Y - X) = 0
    Lấy nghiệm có trị tuyệt đối nhỏ nhất (theo paper gốc).
    """
    channel = pixel_array[:, :, 0]
    P, X, Y, W, Z = _classify_pairs(channel)
    if P < 16:
        return -1.0

    a = 0.5 * (W + Z)
    b = float(2 * X - P)
    c = float(Y - X)

    if abs(a) < 1e-9:
        if abs(b) < 1e-9:
            return 0.0
        p = -c / b
    else:
        disc = b * b - 4 * a * c
        if disc < 0:
            return 0.0
        sqrt_disc = np.sqrt(disc)
        p1 = (-b + sqrt_disc) / (2 * a)
        p2 = (-b - sqrt_disc) / (2 * a)
        p = min((p1, p2), key=abs)

    return float(np.clip(p, 0.0, 1.0))


# ── Chi-squared (secondary) ────────────────────────────────────────────────
def _chi2_raw(pixel_array: np.ndarray) -> tuple[float, float, list[float]]:
    r_channel = pixel_array[:, :, 0].flatten().astype(np.int32)
    hist, _ = np.histogram(r_channel, bins=256, range=(0, 256))
    pair_scores = []
    chi2_total = 0.0
    dof = 0
    for k in range(128):
        n_even = float(hist[2 * k])
        n_odd = float(hist[2 * k + 1])
        expected = (n_even + n_odd) / 2.0
        if expected < 5:
            pair_scores.append(0.0)
            continue
        chi2_k = ((n_even - expected) ** 2 + (n_odd - expected) ** 2) / expected
        pair_scores.append(chi2_k)
        chi2_total += chi2_k
        dof += 1
    p_val = 1.0 - scipy_stats.chi2.cdf(chi2_total, df=max(dof, 1))
    return chi2_total, p_val, pair_scores


# ── Main entry point ───────────────────────────────────────────────────────
def chi_squared_test(
    pixel_array: np.ndarray,
    threshold: float = 0.15,
) -> AnalysisResult:
    """
    threshold = RS embedding rate cutoff (0.0–1.0).
    Default 0.15: nếu ước tính >15% LSBs đã bị thay → DETECTED.
    Image-size independent, robust với mọi loại ảnh.

    Verdict dựa trên rs_rate (giữ nguyên thiết kế R-008) — KHÔNG dùng
    max(rs_rate, spa_rate). Đã thực nghiệm với embed() thật (sequential
    + scattered) và thấy max() không cải thiện recall (RS đã bắt được
    hầu hết true positive) nhưng làm tăng false positive (RS có bias
    overestimate, SPA chính xác hơn nên hiếm khi vượt threshold trước
    RS) → kết hợp OR chỉ kế thừa nhược điểm mà không có lợi ích thực.
    Xem research.md R-009 phần "Phát hiện qua thực nghiệm" để biết chi tiết.
    spa_rate vẫn được trả về như tín hiệu phụ — ước tính chính xác hơn
    rs_rate (sai số thấp hơn ~10x) nên hữu ích để đối chiếu thủ công.
    """
    chi2_total, p_value, pair_scores = _chi2_raw(pixel_array)
    rs_rate = rs_analysis(pixel_array)
    spa_rate = sample_pair_analysis(pixel_array)

    if rs_rate < 0:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "DETECTED" if rs_rate > threshold else "CLEAN"

    return AnalysisResult(
        chi2_score=round(chi2_total, 2),
        p_value=round(p_value, 6),
        rs_rate=round(rs_rate, 4) if rs_rate >= 0 else -1.0,
        spa_rate=round(spa_rate, 4) if spa_rate >= 0 else -1.0,
        verdict=verdict,
        threshold=threshold,
        pair_scores=pair_scores,
    )


# ── Chart ──────────────────────────────────────────────────────────────────
def generate_chart(pixel_array: np.ndarray, title: str = "Steganalysis") -> bytes:
    r_channel = pixel_array[:, :, 0].flatten().astype(np.int32)
    hist, _ = np.histogram(r_channel, bins=256, range=(0, 256))
    even_vals = hist[0::2].astype(float)
    odd_vals = hist[1::2].astype(float)
    x = np.arange(128)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), facecolor="#0A0F0D")
    fig.suptitle(title, color="#00FF88", fontsize=13, fontweight="bold")

    ax1.bar(range(256), hist, color="#00D4FF", alpha=0.7, width=1.0)
    ax1.set_facecolor("#111714")
    ax1.set_title("R Channel Histogram", color="#94A3B8", fontsize=10)
    ax1.tick_params(colors="#94A3B8")
    for spine in ax1.spines.values():
        spine.set_edgecolor("#1e2920")

    diff = np.abs(even_vals - odd_vals)
    mean_diff = np.mean(diff)
    colors = ["#FF4444" if d < mean_diff * 0.5 else "#00FF88" for d in diff]
    bar_w = 0.4
    ax2.bar(x - bar_w / 2, even_vals, bar_w, label="2k (even)", color="#00D4FF", alpha=0.8)
    ax2.bar(x + bar_w / 2, odd_vals, bar_w, label="2k+1 (odd)", color=colors, alpha=0.8)
    ax2.set_facecolor("#111714")
    ax2.set_title("Pair (2k, 2k+1) — red = suspiciously equal", color="#94A3B8", fontsize=10)
    ax2.legend(facecolor="#1e2920", labelcolor="#F0FFF4", fontsize=8)
    ax2.tick_params(colors="#94A3B8")
    for spine in ax2.spines.values():
        spine.set_edgecolor("#1e2920")

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor="#0A0F0D")
    plt.close(fig)
    return buf.getvalue()
