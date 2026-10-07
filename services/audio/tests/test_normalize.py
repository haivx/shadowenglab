"""Test chuẩn hoá bản ghi: nhận diện container và ffmpeg thật (REC-02, T-02-25)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from audio_service.lesson import normalize
from audio_service.lesson.normalize import MP4_DEMUXER, WEBM_DEMUXER, sniff_demuxer

SR = 16000


def _encode(seconds: float, out: Path, *codec_args: str, sr: int = SR) -> None:
    wav = out.with_suffix(".src.wav")
    t = np.arange(int(sr * seconds)) / sr
    sf.write(wav, (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr, subtype="PCM_16")
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(wav), *codec_args, str(out)],
        check=True,
    )


def _info(path: Path) -> sf._SoundFileInfo:
    return sf.info(path)


# --- sniff_demuxer ---------------------------------------------------------------------------


def test_sniff_webm_header() -> None:
    assert sniff_demuxer(b"\x1aE\xdf\xa3\x01\x00\x00\x00\x00\x00\x00\x1fB\x86\x81") == WEBM_DEMUXER


def test_sniff_mp4_ftyp() -> None:
    assert sniff_demuxer(b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00") == MP4_DEMUXER


@pytest.mark.parametrize(
    "head",
    [
        b"#EXTM3U\n#EXT-X-VERSION:3\nfile:///etc/hosts\n",
        b"RIFF\x24\x08\x00\x00WAVEfmt ",
        b"",
        b"hello world, this is plain text",
        b"\x00\x00\x00",
    ],
    ids=["m3u8-playlist", "wav", "empty", "text", "too-short"],
)
def test_sniff_rejects_everything_else_including_m3u8(head: bytes) -> None:
    assert sniff_demuxer(head) is None


# --- normalize_to_wav16k (ffmpeg thật) -------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "codec_args", "demuxer"),
    [
        ("rec.webm", ("-c:a", "libopus"), WEBM_DEMUXER),
        ("rec.mp4", ("-c:a", "aac"), MP4_DEMUXER),
        (
            "frag.mp4",
            ("-c:a", "aac", "-movflags", "frag_keyframe+empty_moov"),
            MP4_DEMUXER,
        ),
    ],
    ids=["webm-opus", "mp4-aac", "fragmented-mp4"],
)
def test_normalizes_browser_containers_to_16k_mono_pcm16(
    tmp_path: Path, name: str, codec_args: tuple[str, ...], demuxer: str
) -> None:
    src = tmp_path / name
    _encode(1.0, src, *codec_args, sr=48000)
    dst = tmp_path / "out.wav"

    normalize.normalize_to_wav16k(src, dst, demuxer)

    info = _info(dst)
    assert info.samplerate == 16000
    assert info.channels == 1
    assert info.subtype == "PCM_16"
    assert abs(info.duration - 1.0) < 0.1


def test_input_longer_than_the_limit_is_cut(tmp_path: Path) -> None:
    src = tmp_path / "long.webm"
    _encode(70.0, src, "-c:a", "libopus")
    dst = tmp_path / "out.wav"

    normalize.normalize_to_wav16k(src, dst, WEBM_DEMUXER)

    assert 60.5 <= _info(dst).duration <= 61.1


def test_demuxer_outside_the_whitelist_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        normalize.normalize_to_wav16k(tmp_path / "x", tmp_path / "y.wav", "hls")


def test_ffmpeg_never_sees_a_playlist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Một playlist m3u8 không qua được sniff, nên không bao giờ tới ffmpeg."""
    calls: list[list[str]] = []
    monkeypatch.setattr(
        normalize.subprocess, "run", lambda cmd, **_kw: calls.append(list(cmd)) or None
    )
    playlist = b"#EXTM3U\n#EXT-X-VERSION:3\n#EXTINF:1,\nfile:///etc/hosts\n"

    assert sniff_demuxer(playlist[:16]) is None
    assert calls == []


def test_argv_has_explicit_demuxer_before_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        normalize.subprocess, "run", lambda cmd, **_kw: calls.append(list(cmd)) or None
    )

    normalize.normalize_to_wav16k(tmp_path / "a.bin", tmp_path / "b.wav", WEBM_DEMUXER)

    argv = calls[0]
    assert argv[argv.index("-f") + 1] == WEBM_DEMUXER
    assert argv.index("-f") < argv.index("-i")
    assert argv[argv.index("-ar") + 1] == "16000"
    assert argv[argv.index("-ac") + 1] == "1"
    assert argv[argv.index("-c:a") + 1] == "pcm_s16le"
