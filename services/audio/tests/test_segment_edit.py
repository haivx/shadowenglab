"""PATCH /lessons/{id}/segments/{i}: sửa text câu giữ căn chỉnh từ, xoá translation (PLY-04, D-16).

Không nạp model, không gọi mạng; bài được ghi thẳng xuống DATA_DIR tạm.
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from audio_service.config import get_settings, lesson_json_path
from audio_service.contracts_gen import Lesson
from audio_service.lesson import store
from audio_service.lesson.segment_ops import apply_text_edit, normalize_text
from audio_service.main import create_app

LESSON_ID = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"
VIDEO_ID = "dUDi-F6eAvk"


def make_lesson_dict(
    *, status: str = "ready", end_extra_ms: int = 0, with_translation: bool = True
) -> dict[str, Any]:
    first: dict[str, Any] = {
        "index": 0,
        "text": "Hello there my friend.",
        "start": 0.5,
        "end": 3.8,
        "endExtraMs": end_extra_ms,
        "words": [
            {
                "i": 0,
                "text": "Hello",
                "start": 0.5,
                "end": 1.1,
                "asrProb": 0.9,
                "ipa": "həloʊ",
                "refConfidence": 0.8,
                "prominence": 1.5,
            },
            {"i": 1, "text": "there", "start": 1.2, "end": 1.9, "asrProb": 0.8},
            {"i": 2, "text": "my", "start": 2.0, "end": 2.4, "asrProb": 0.95, "ipa": "maɪ"},
            {"i": 3, "text": "friend.", "start": 2.5, "end": 3.8, "asrProb": 0.7},
        ],
    }
    if with_translation:
        first["translation"] = "Xin chào bạn của tôi."
    second: dict[str, Any] = {
        "index": 1,
        "text": "How are you today?",
        "start": 4.4,
        "end": 7.6,
        "endExtraMs": 0,
        "words": [
            {"i": 0, "text": "How", "start": 4.4, "end": 4.8, "asrProb": 0.9},
            {"i": 1, "text": "are", "start": 4.9, "end": 5.3, "asrProb": 0.85},
            {"i": 2, "text": "you", "start": 5.4, "end": 5.8, "asrProb": 0.99},
            {"i": 3, "text": "today?", "start": 5.9, "end": 7.6, "asrProb": 0.6},
        ],
    }
    return {
        "id": LESSON_ID,
        "videoId": VIDEO_ID,
        "title": "Fake title",
        "durationSec": 12.0,
        "range": {"start": 0.0, "end": 12.0},
        "status": status,
        "segments": [first, second],
        "createdAt": "2026-10-07T00:00:00Z",
    }


def write_lesson(**kwargs: Any) -> None:
    store.save_lesson(Lesson.model_validate(make_lesson_dict(**kwargs)))


def read_json() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(lesson_json_path(LESSON_ID).read_text(encoding="utf-8"))
    return data


def assert_no_null(value: object) -> None:
    if isinstance(value, dict):
        for item in value.values():
            assert_no_null(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_null(item)
    else:
        assert value is not None


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path.resolve()
    get_settings.cache_clear()


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), base_url="http://127.0.0.1")


def patch(client: TestClient, text: object, index: int = 0) -> Any:
    return client.patch(f"/lessons/{LESSON_ID}/segments/{index}", json={"text": text})


def test_same_token_count_edit_keeps_timings_and_ipa_and_replaces_word_texts(
    client: TestClient, data_dir: Path
) -> None:
    write_lesson()
    res = patch(client, "Hello there our friend!")
    assert res.status_code == 200
    body = res.json()
    assert body["text"] == "Hello there our friend!"
    assert [w["text"] for w in body["words"]] == ["Hello", "there", "our", "friend!"]
    before = make_lesson_dict()["segments"][0]["words"]
    for old, new in zip(before, body["words"], strict=True):
        assert {k: v for k, v in new.items() if k != "text"} == {
            k: v for k, v in old.items() if k != "text"
        }
    assert body["words"][2]["ipa"] == "maɪ"  # ipa của từ "my" vẫn đứng ở vị trí đó
    assert body["start"] == 0.5 and body["end"] == 3.8


def test_translation_key_is_removed_from_response_and_disk(
    client: TestClient, data_dir: Path
) -> None:
    write_lesson()
    res = patch(client, "Hello there our friend!")
    assert "translation" not in res.json()
    assert "translation" not in read_json()["segments"][0]


def test_edit_persists_to_lesson_json_and_leaves_other_segments(
    client: TestClient, data_dir: Path
) -> None:
    write_lesson()
    patch(client, "Hello there our friend!")
    saved = read_json()
    assert saved["segments"][0]["text"] == "Hello there our friend!"
    assert saved["segments"][1] == make_lesson_dict()["segments"][1]
    assert saved["status"] == "ready"


def test_different_token_count_keeps_words_untouched_and_only_changes_text(
    client: TestClient, data_dir: Path
) -> None:
    write_lesson()
    res = patch(client, "Hello my friend.")
    body = res.json()
    assert res.status_code == 200
    assert body["text"] == "Hello my friend."
    assert body["words"] == make_lesson_dict()["segments"][0]["words"]
    assert "translation" not in body


def test_text_is_stored_nfc_normalized(client: TestClient, data_dir: Path) -> None:
    write_lesson()
    decomposed = unicodedata.normalize("NFD", "café there our friend")  # e + dấu sắc rời
    assert decomposed != unicodedata.normalize("NFC", decomposed)
    res = patch(client, decomposed)
    stored = read_json()["segments"][0]["text"]
    assert res.status_code == 200
    assert stored == "café there our friend"
    assert stored == unicodedata.normalize("NFC", stored)
    assert res.json()["text"] == stored


def test_length_is_counted_after_normalization(client: TestClient, data_dir: Path) -> None:
    write_lesson()
    # 300 chữ "é" tổ hợp = 600 code point thô nhưng 300 sau NFC: phải được chấp nhận.
    decomposed = unicodedata.normalize("NFD", "é" * 300)
    assert len(decomposed) == 600
    assert patch(client, decomposed).status_code == 200


def test_whitespace_is_trimmed_and_collapsed(client: TestClient, data_dir: Path) -> None:
    write_lesson()
    res = patch(client, "  Hello \t there\n\n our   friend  ")
    assert res.json()["text"] == "Hello there our friend"
    assert [w["text"] for w in res.json()["words"]] == ["Hello", "there", "our", "friend"]


@pytest.mark.parametrize("bad", ["", "   ", "\n\t "])
def test_empty_or_whitespace_only_text_is_422_invalid_request(
    client: TestClient, data_dir: Path, bad: str
) -> None:
    write_lesson()
    res = patch(client, bad)
    assert res.status_code == 422
    assert res.json() == {
        "code": "invalid_request",
        "message": "Câu không được để trống hoặc dài quá 500 ký tự.",
    }
    assert read_json()["segments"][0]["text"] == "Hello there my friend."


def test_500_code_points_accepted_501_rejected(client: TestClient, data_dir: Path) -> None:
    write_lesson()
    assert patch(client, "a" * 500).status_code == 200
    res = patch(client, "a" * 501)
    assert res.status_code == 422
    assert res.json()["code"] == "invalid_request"
    assert read_json()["segments"][0]["text"] == "a" * 500


@pytest.mark.parametrize("body", [{}, {"text": 5}, {"text": None}])
def test_malformed_body_is_422_invalid_request(
    client: TestClient, data_dir: Path, body: dict[str, object]
) -> None:
    write_lesson()
    res = client.patch(f"/lessons/{LESSON_ID}/segments/0", json=body)
    assert res.status_code == 422
    assert res.json()["code"] == "invalid_request"


@pytest.mark.parametrize("status", ["queued", "downloading", "analyzing", "failed"])
def test_lesson_not_ready_is_409_invalid_state(
    client: TestClient, data_dir: Path, status: str
) -> None:
    write_lesson(status=status)
    res = patch(client, "Hello there our friend!")
    assert res.status_code == 409
    assert res.json()["code"] == "invalid_state"
    assert read_json()["segments"][0]["text"] == "Hello there my friend."


def test_unknown_lesson_is_404_not_found(client: TestClient, data_dir: Path) -> None:
    res = patch(client, "Hello")
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"


def test_malformed_lesson_id_is_404_not_found(client: TestClient, data_dir: Path) -> None:
    res = client.patch("/lessons/not-a-ulid/segments/0", json={"text": "Hello"})
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"


@pytest.mark.parametrize("index", [2, 99, -1])
def test_segment_index_out_of_range_is_404_invalid_segment(
    client: TestClient, data_dir: Path, index: int
) -> None:
    write_lesson()
    res = patch(client, "Hello", index=index)
    assert res.status_code == 404
    assert res.json()["code"] == "invalid_segment"


def test_response_and_disk_never_contain_null(client: TestClient, data_dir: Path) -> None:
    write_lesson()
    res = patch(client, "Hello there our friend!")
    assert_no_null(res.json())
    assert_no_null(read_json())
    res = patch(client, "Short one")
    assert_no_null(res.json())
    assert_no_null(read_json())


def test_error_bodies_do_not_leak_paths_or_input(client: TestClient, data_dir: Path) -> None:
    write_lesson(status="queued")
    res = patch(client, "secret-input-xyz")
    assert str(data_dir) not in res.text
    assert "secret-input-xyz" not in res.text


def test_normalize_text_is_idempotent() -> None:
    once = normalize_text("  á  b ")
    assert once == "á b"
    assert normalize_text(once) == once


def test_apply_text_edit_does_not_mutate_its_input() -> None:
    lesson = Lesson.model_validate(make_lesson_dict())
    original = lesson.segments[0]
    edited = apply_text_edit(original, "Hello there our friend!")
    assert original.text == "Hello there my friend."
    assert original.translation == "Xin chào bạn của tôi."
    assert edited.translation is None
    assert "translation" not in edited.model_dump(by_alias=True, exclude_unset=True)
