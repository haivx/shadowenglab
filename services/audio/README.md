# services/audio — Pipeline audio (Python 3.11, FastAPI, quản lý bằng uv)

- `lesson/`: yt-dlp → Demucs → mlx-whisper → tách câu → feature bản gốc (F0, prominence, PPG)
- `scoring/`: Lớp A (PPG + DTW), Lớp B (parselmouth), Lớp C (rule engine + gợi ý)

Spec: `docs/product.md` mục 3. Chưa có code. Skeleton được dựng trong P0 · C1–C3.
