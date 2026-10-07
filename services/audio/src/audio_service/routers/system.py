"""Router system: trạng thái hệ thống (model, key, thư mục dữ liệu đang dùng).

Không prefix: mỗi endpoint tự khai báo đường dẫn đầy đủ.
"""

from fastapi import APIRouter

from audio_service.contracts_gen import SystemStatus
from audio_service.system_status import build_status

router = APIRouter(tags=["system"])


@router.get("/system/status", response_model=SystemStatus, response_model_exclude_unset=True)
def system_status() -> SystemStatus:
    """Model (missing/loading/ready), hasKey (+ maskedKey), activeDataDir. Luôn 200."""
    return build_status()
