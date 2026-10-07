"""download.py: metadata (channel / live_status / availability), H.264 + khoá theo video.

Không mạng, không ffmpeg/ffprobe thật: `yt_dlp.YoutubeDL` và `subprocess.run` là bản giả.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from audio_service.config import get_settings, video_dir
from audio_service.lesson import download

VIDEO_ID = "dUDi-F6eAvk"


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path.resolve()
    get_settings.cache_clear()


class FakeYoutubeDL:
    """Thay yt_dlp.YoutubeDL cho extract_info (download=False)."""

    raw: dict[str, Any] | None = None

    def __init__(self, opts: dict[str, Any]) -> None:
        self.opts = opts

    def __enter__(self) -> FakeYoutubeDL:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def extract_info(self, _url: str, download: bool = True) -> dict[str, Any] | None:
        assert download is False
        return type(self).raw


def install_fake_ydl(monkeypatch: pytest.MonkeyPatch, raw: dict[str, Any] | None) -> None:
    FakeYoutubeDL.raw = raw
    monkeypatch.setattr(download.yt_dlp, "YoutubeDL", FakeYoutubeDL)


# ------------------------------------------------------------------ fetch_info


def test_fetch_info_reads_old_cache_without_new_keys(data_dir: Path) -> None:
    path = video_dir(VIDEO_ID) / "info.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"videoId": VIDEO_ID, "title": "Old", "durationSec": 61.5}), encoding="utf-8"
    )
    info = download.fetch_info(VIDEO_ID)
    assert (info.title, info.duration_sec) == ("Old", 61.5)
    assert info.thumbnail_url is None
    assert info.channel is None
    assert info.live_status is None
    assert info.availability is None


def test_fetch_info_cache_round_trips_the_new_keys(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fake_ydl(
        monkeypatch,
        {
            "title": "T",
            "duration": 30,
            "channel": "HBO Max",
            "live_status": "not_live",
            "availability": "public",
            "thumbnail": "https://img/x.jpg",
        },
    )
    first = download.fetch_info(VIDEO_ID)
    assert (first.channel, first.live_status, first.availability) == (
        "HBO Max",
        "not_live",
        "public",
    )
    payload = json.loads((video_dir(VIDEO_ID) / "info.json").read_text(encoding="utf-8"))
    assert payload["channel"] == "HBO Max"
    assert payload["liveStatus"] == "not_live"
    assert payload["availability"] == "public"

    install_fake_ydl(monkeypatch, None)  # lần hai phải đọc cache, không hỏi yt-dlp
    assert download.fetch_info(VIDEO_ID) == first


def test_fetch_info_omits_absent_keys_from_the_cache(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fake_ydl(monkeypatch, {"title": "T", "duration": 30})
    info = download.fetch_info(VIDEO_ID)
    assert info.channel is None and info.live_status is None and info.availability is None
    payload = json.loads((video_dir(VIDEO_ID) / "info.json").read_text(encoding="utf-8"))
    for key in ("channel", "liveStatus", "availability", "thumbnailUrl"):
        assert key not in payload


@pytest.mark.parametrize("status", ["is_live", "is_upcoming"])
def test_fetch_info_reports_live_video_without_duration_and_does_not_cache_it(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    install_fake_ydl(monkeypatch, {"title": "Live now", "duration": None, "live_status": status})
    info = download.fetch_info(VIDEO_ID)
    assert info.live_status == status
    assert not (video_dir(VIDEO_ID) / "info.json").exists()  # trạng thái live đổi theo thời gian


def test_fetch_info_still_rejects_a_non_live_video_without_duration(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fake_ydl(monkeypatch, {"title": "T", "duration": None, "live_status": "not_live"})
    with pytest.raises(RuntimeError):
        download.fetch_info(VIDEO_ID)


# ------------------------------------------------------------------ format selector (D-19)


def test_format_prefers_avc1_mp4a_and_keeps_old_selector_as_fallback() -> None:
    fmt = download._FORMAT
    assert fmt.startswith("bv*[height<=480][vcodec^=avc1]+ba[acodec^=mp4a]/")
    assert "b[height<=480][vcodec^=avc1]" in fmt
    # selector cũ vẫn còn ở cuối làm đường lùi: ưu tiên H.264 nhưng không bao giờ tải hỏng
    assert fmt.endswith("/bv*[height<=480]+ba/b[height<=480]/b")


# ----------------------------------------------------------- ffprobe / ffmpeg (không binary thật)


class Completed:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout
        self.returncode = 0


class FakeRun:
    """Thay subprocess.run: ghi argv, ffprobe trả `codec`, ffmpeg ghi file đích (argv cuối)."""

    def __init__(self, codec: str = "h264", fail_ffmpeg: bool = False) -> None:
        self.codec = codec
        self.fail_ffmpeg = fail_ffmpeg
        self.calls: list[list[str]] = []
        self.kwargs: list[dict[str, Any]] = []

    def __call__(self, cmd: list[str], **kwargs: Any) -> Completed:
        self.calls.append(list(cmd))
        self.kwargs.append(kwargs)
        if cmd[0] == "ffprobe":
            return Completed(self.codec + "\n")
        if self.fail_ffmpeg:
            Path(cmd[-1]).write_bytes(b"half written")
            raise download.subprocess.CalledProcessError(1, cmd)
        Path(cmd[-1]).write_bytes(b"transcoded h264")
        return Completed()


def test_probe_video_codec_runs_ffprobe_argv_list_with_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run = FakeRun(codec="av1")
    monkeypatch.setattr(download.subprocess, "run", run)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    assert download.probe_video_codec(video) == "av1"
    cmd = run.calls[0]
    assert cmd[:2] == ["ffprobe", "-v"]
    assert "stream=codec_name" in cmd and "v:0" in cmd and str(video) == cmd[-1]
    assert run.kwargs[0]["timeout"] == 30
    assert not run.kwargs[0].get("shell")


def test_probe_video_codec_raises_when_ffprobe_prints_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(download.subprocess, "run", FakeRun(codec=""))
    with pytest.raises(RuntimeError):
        download.probe_video_codec(tmp_path / "v.mp4")


def test_ensure_h264_does_not_transcode_h264(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run = FakeRun(codec="h264")
    monkeypatch.setattr(download.subprocess, "run", run)
    video = tmp_path / "video.mp4"
    video.write_bytes(b"original")
    download.ensure_h264(video)
    assert [c[0] for c in run.calls] == ["ffprobe"]
    assert video.read_bytes() == b"original"


def test_ensure_h264_transcodes_av1_to_temp_then_replaces(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run = FakeRun(codec="av1")
    monkeypatch.setattr(download.subprocess, "run", run)
    video = tmp_path / "video.mp4"
    video.write_bytes(b"av1 bytes")
    download.ensure_h264(video)

    ffmpeg = next(c for c in run.calls if c[0] == "ffmpeg")
    assert "-nostdin" in ffmpeg and "libx264" in ffmpeg and "aac" in ffmpeg
    assert str(video) in ffmpeg  # đầu vào
    assert ffmpeg[-1] != str(video)  # đầu ra là file tạm, rồi mới os.replace
    ffmpeg_kwargs = run.kwargs[run.calls.index(ffmpeg)]
    assert ffmpeg_kwargs["timeout"] == 600 and ffmpeg_kwargs["check"] is True
    assert video.read_bytes() == b"transcoded h264"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["video.mp4"]  # không để lại file tạm


def test_ensure_h264_failure_keeps_original_and_leaves_no_temp_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(download.subprocess, "run", FakeRun(codec="vp9", fail_ffmpeg=True))
    video = tmp_path / "video.mp4"
    video.write_bytes(b"vp9 bytes")
    with pytest.raises(download.subprocess.CalledProcessError):
        download.ensure_h264(video)
    assert video.read_bytes() == b"vp9 bytes"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["video.mp4"]


# ------------------------------------------------------------ download_video + khoá theo video


class FakeDownloader:
    """Thay yt_dlp.YoutubeDL cho `.download`: ghi file vào đúng chỗ outtmpl chỉ định."""

    def __init__(self, *, barrier: threading.Barrier | None = None) -> None:
        self.barrier = barrier
        self.calls: list[str] = []
        self.opts_seen: list[dict[str, Any]] = []
        self.target_visible_during_download: list[bool] = []
        self._lock = threading.Lock()

    def __call__(self, opts: dict[str, Any]) -> FakeDownloader.Session:
        return FakeDownloader.Session(self, opts)

    class Session:
        def __init__(self, owner: FakeDownloader, opts: dict[str, Any]) -> None:
            self.owner = owner
            self.opts = opts

        def __enter__(self) -> FakeDownloader.Session:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def download(self, urls: list[str]) -> None:
            owner = self.owner
            with owner._lock:
                owner.calls.append(urls[0])
                owner.opts_seen.append(self.opts)
            out = Path(str(self.opts["outtmpl"]).replace("%(ext)s", "mp4"))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"downloaded")
            owner.target_visible_during_download.append((out.parent / "video.mp4").exists())
            if owner.barrier is not None:
                owner.barrier.wait(timeout=5)  # chỉ qua được khi hai lần tải chạy song song
            time.sleep(0.05)


def install_downloader(
    monkeypatch: pytest.MonkeyPatch, downloader: FakeDownloader, *, codec: str = "h264"
) -> FakeRun:
    run = FakeRun(codec=codec)
    monkeypatch.setattr(download.yt_dlp, "YoutubeDL", downloader)
    monkeypatch.setattr(download.subprocess, "run", run)
    return run


def test_download_video_uses_h264_format_and_publishes_only_the_final_file(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    downloader = FakeDownloader()
    install_downloader(monkeypatch, downloader)
    path = download.download_video(VIDEO_ID)
    assert path == video_dir(VIDEO_ID) / "video.mp4"
    assert path.read_bytes() == b"downloaded"
    assert downloader.opts_seen[0]["format"] == download._FORMAT
    assert downloader.opts_seen[0]["merge_output_format"] == "mp4"
    assert downloader.target_visible_during_download == [False]  # nửa chừng không thấy video.mp4
    assert sorted(p.name for p in video_dir(VIDEO_ID).iterdir()) == ["video.mp4"]


def test_download_video_transcodes_before_video_mp4_becomes_visible(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    downloader = FakeDownloader()
    run = install_downloader(monkeypatch, downloader, codec="av1")
    path = download.download_video(VIDEO_ID)
    assert any(c[0] == "ffmpeg" for c in run.calls)
    assert path.read_bytes() == b"transcoded h264"


def test_download_video_failed_transcode_never_publishes_video_mp4(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(download.yt_dlp, "YoutubeDL", FakeDownloader())
    monkeypatch.setattr(download.subprocess, "run", FakeRun(codec="av1", fail_ffmpeg=True))
    with pytest.raises(download.subprocess.CalledProcessError):
        download.download_video(VIDEO_ID)
    assert list(video_dir(VIDEO_ID).iterdir()) == []


def test_download_video_cache_hit_does_not_download(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = video_dir(VIDEO_ID) / "video.mp4"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"cached")
    downloader = FakeDownloader()
    install_downloader(monkeypatch, downloader)
    assert download.download_video(VIDEO_ID) == target
    assert downloader.calls == []


def test_two_threads_downloading_the_same_video_download_once(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    downloader = FakeDownloader()
    install_downloader(monkeypatch, downloader)
    results: list[Path] = []
    errors: list[BaseException] = []

    def work() -> None:
        try:
            results.append(download.download_video(VIDEO_ID))
        except BaseException as exc:  # noqa: BLE001 - test thu lỗi để assert
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert errors == []
    assert len(downloader.calls) == 1
    assert len(results) == 2 and results[0] == results[1]


def test_different_videos_download_in_parallel(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    downloader = FakeDownloader(barrier=threading.Barrier(2))  # nối tiếp thì barrier hết hạn
    install_downloader(monkeypatch, downloader)
    errors: list[BaseException] = []

    def work(video_id: str) -> None:
        try:
            download.download_video(video_id)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(v,)) for v in (VIDEO_ID, "aaaaaaaaaaa")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert errors == []
    assert len(downloader.calls) == 2


def test_video_lock_is_per_video_and_reentrant() -> None:
    lock = download._video_lock(VIDEO_ID)
    assert download._video_lock(VIDEO_ID) is lock
    assert download._video_lock("aaaaaaaaaaa") is not lock
    with lock, lock:  # reload giữ khoá rồi gọi download_video, nên phải reentrant
        pass


# ------------------------------------------------------------------ reload_video


def test_reload_video_removes_old_file_before_downloading(data_dir: Path) -> None:
    target = video_dir(VIDEO_ID) / "video.mp4"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"broken av1")
    seen: list[bool] = []

    def fake_download(video_id: str) -> Path:
        seen.append(target.exists())
        target.write_bytes(b"fresh")
        return target

    download.reload_video(VIDEO_ID, fake_download)
    assert seen == [False]
    assert target.read_bytes() == b"fresh"
    assert sorted(p.name for p in target.parent.iterdir()) == ["video.mp4"]


def test_reload_video_restores_the_old_file_when_download_fails(data_dir: Path) -> None:
    target = video_dir(VIDEO_ID) / "video.mp4"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old but playable")

    def failing(_video_id: str) -> Path:
        raise RuntimeError("network down")

    with pytest.raises(RuntimeError):
        download.reload_video(VIDEO_ID, failing)
    assert target.read_bytes() == b"old but playable"
    assert sorted(p.name for p in target.parent.iterdir()) == ["video.mp4"]


def test_reload_video_works_when_the_file_is_already_missing(data_dir: Path) -> None:
    target = video_dir(VIDEO_ID) / "video.mp4"

    def fake_download(_video_id: str) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"fresh")
        return target

    download.reload_video(VIDEO_ID, fake_download)
    assert target.read_bytes() == b"fresh"
