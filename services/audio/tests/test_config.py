from collections.abc import Iterator
from pathlib import Path

import pytest

from audio_service.config import (
    REPO_ROOT,
    InvalidIdError,
    Settings,
    data_root,
    get_settings,
    lesson_dir,
    lesson_json_path,
    segment_features_path,
    video_asset_path,
    video_dir,
)

ULID = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"
VIDEO_ID = "dUDi-F6eAvk"


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path.resolve()
    get_settings.cache_clear()


def test_tilde_data_dir_expands_to_absolute_home_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DATA_DIR", "~/x")
    get_settings.cache_clear()
    try:
        assert data_root() == (tmp_path / "x").resolve()
        assert data_root().is_absolute()
    finally:
        get_settings.cache_clear()


def test_env_file_is_anchored_at_repo_root() -> None:
    assert Settings.model_config["env_file"] == REPO_ROOT / ".env"
    assert (REPO_ROOT / "pnpm-workspace.yaml").is_file()


def test_lesson_paths_follow_d08_layout(data_dir: Path) -> None:
    assert lesson_dir(ULID) == data_dir / "lessons" / ULID
    assert lesson_json_path(ULID) == data_dir / "lessons" / ULID / "lesson.json"
    assert segment_features_path(ULID, 7) == data_dir / "lessons" / ULID / "seg" / "0007.npz"


def test_negative_segment_index_rejected(data_dir: Path) -> None:
    with pytest.raises(InvalidIdError):
        segment_features_path(ULID, -1)


@pytest.mark.parametrize("bad", ["../x", "01hzx3y7q8k2m4n6p8r0s2t4v6", ULID[:25], ULID + "0", ""])
def test_invalid_lesson_ids_rejected(data_dir: Path, bad: str) -> None:
    with pytest.raises(InvalidIdError):
        lesson_dir(bad)
    with pytest.raises(InvalidIdError):
        lesson_json_path(bad)
    with pytest.raises(InvalidIdError):
        segment_features_path(bad, 0)


@pytest.mark.parametrize("bad", ["../../etc", "abc", VIDEO_ID + "x", "", "dUDi/F6eAvk"])
def test_invalid_video_ids_rejected(data_dir: Path, bad: str) -> None:
    with pytest.raises(InvalidIdError):
        video_dir(bad)
    with pytest.raises(InvalidIdError):
        video_asset_path(bad, "vocals.wav")


def test_video_asset_path(data_dir: Path) -> None:
    assert video_asset_path(VIDEO_ID, "vocals.wav") == data_dir / "videos" / VIDEO_ID / "vocals.wav"


def test_unknown_video_asset_rejected(data_dir: Path) -> None:
    with pytest.raises(InvalidIdError):
        video_asset_path(VIDEO_ID, "../../x")  # type: ignore[arg-type]


def test_symlinked_lesson_dir_escaping_data_dir_rejected(data_dir: Path, tmp_path_factory) -> None:
    outside = tmp_path_factory.mktemp("outside")
    (data_dir / "lessons").mkdir()
    (data_dir / "lessons" / ULID).symlink_to(outside, target_is_directory=True)
    with pytest.raises(InvalidIdError):
        lesson_dir(ULID)
    with pytest.raises(InvalidIdError):
        lesson_json_path(ULID)
