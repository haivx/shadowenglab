"""Bộ công cụ chấm lại và đếm cho eval nội bộ Phase 4 (EVL-02): nạp case, chấm lại WAV, đếm, report.

`eval/` không phải package của service. Script chạy bằng
`uv run --project services/audio --frozen python eval/<x>.py`; thư mục `eval/` tự vào `sys.path`
nên `import evalkit` hoạt động, còn `audio_service` đến từ venv của `services/audio`.

- `cases`: nạp `cases.jsonl` bằng pydantic `EvalCase`, kiểm bất biến, dấu nhận diện câu (D-05).
- `rescore`: tìm bài/clip, chấm lại WAV đã lưu bằng scorer hiện tại (D-06), mốc tự so (D-18a).
- `counting`: bảng mã D-10, phân loại TP/FP/FN, tally và khoảng tin cậy Wilson.
- `report`: dựng `report.md`.
"""
