"""Cách ly toàn bộ test khỏi máy của Liam (02-11, T-02-31).

Fixture autouse này chạy trước mọi test:
- `SHADOWENGLAB_CONFIG_DIR` / `SHADOWENGLAB_ENV_FILE` trỏ vào thư mục tạm, nên test không đọc hay
  ghi `~/.config/shadowenglab` hay `.env` ở gốc repo thật.
- `OPENAI_API_KEY` bị gỡ khỏi môi trường (và được khôi phục sau test, kể cả khi test tự đặt lại).
- Cache `get_settings()` được xoá trước/sau mỗi test (thư mục dữ liệu được phân giải một lần).
- Warm-up dùng chung được đặt về "mọi model thiếu": lifespan thật (app không inject deps) không
  bao giờ nạp model thật trong test.
"""

from collections.abc import Iterator

import pytest

from audio_service import system_status
from audio_service.config import get_settings


@pytest.fixture(autouse=True)
def _isolate_machine_state(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    # Thư mục riêng (không phải tmp_path của test): test nào dùng tmp_path làm DATA_DIR vẫn sạch.
    machine = tmp_path_factory.mktemp("machine")
    config_dir = machine / "config"
    config_dir.mkdir()
    monkeypatch.setenv("SHADOWENGLAB_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("SHADOWENGLAB_ENV_FILE", str(machine / "env"))
    # setenv rồi delenv: undo của monkeypatch khôi phục trạng thái ban đầu (không có biến) kể cả
    # khi test ghi `os.environ["OPENAI_API_KEY"]` trực tiếp (hot reload, D-11).
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder")
    monkeypatch.delenv("OPENAI_API_KEY")
    get_settings.cache_clear()
    system_status.reset_warm_up(
        system_status.WarmUp(
            system_status.model_cache_states(
                check=lambda: {"demucs": False, "whisper": False, "wav2vec2": False}
            )
        )
    )
    yield
    get_settings.cache_clear()
    system_status.reset_warm_up()
