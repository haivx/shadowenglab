"""Router library: thư viện bài học (danh sách, xoá, tiến độ).

Chưa có endpoint: plan 02-06 sẽ thêm vào đây mà không phải sửa `main.py` (tiền lệ router
`scoring` ở Phase 1). Không prefix: mỗi endpoint tự khai báo đường dẫn đầy đủ.
"""

from fastapi import APIRouter

router = APIRouter(tags=["library"])
