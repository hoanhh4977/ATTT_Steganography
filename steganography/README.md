# StegoTool — Image Steganography

Web tool giấu tin trong ảnh với FastAPI + vanilla JS. Core LSB implement từ đầu bằng numpy, mã hóa AES-128 CBC, steganalysis Chi-squared.

## Cài đặt

```bash
cd steganography
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Chạy server

```bash
uvicorn app.main:app --reload
```

Mở trình duyệt: **http://localhost:8000**

## 3 tính năng

| Tab | Mô tả |
|-----|-------|
| **EMBED** | Upload ảnh PNG/BMP, nhập message + password → tải về ảnh stego |
| **EXTRACT** | Upload ảnh stego + password → giải mã message gốc |
| **ANALYZE** | Chi-squared steganalysis → phát hiện có tin giấu không |

