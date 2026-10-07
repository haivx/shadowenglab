"""Test IPA từ PPG (D-14, D-20): giải mã CTC, gán phone vào từ, ẩn từ không chắc. Không model."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np

from audio_service.lesson import ipa
from audio_service.lesson.ipa import (
    IPA_MIN_CONF,
    IPA_TOL_FRAMES,
    PPG_FPS,
    decode_phones,
    ipa_for_segment,
)

# 0-3 là blank/special như vocab espeak thật; 4 "h", 5 "aɪ".
VOCAB = {0: "<pad>", 1: "<s>", 2: "</s>", 3: "<unk>", 4: "h", 5: "aɪ"}
N_CLASSES = 6


def make_ppg(peaks: dict[int, tuple[int, float]], frames: int) -> np.ndarray:
    """PPG (frames, 6) toàn blank; `peaks[frame] = (token, prob)` ghi đè frame đó."""
    ppg = np.zeros((frames, N_CLASSES), dtype=np.float32)
    ppg[:, 0] = 1.0
    for frame, (token, prob) in peaks.items():
        ppg[frame, :] = (1.0 - prob) / (N_CLASSES - 1)
        ppg[frame, token] = prob
    return ppg


def test_constants_are_the_locked_values() -> None:
    assert IPA_MIN_CONF == 0.7
    assert IPA_TOL_FRAMES == 2
    assert PPG_FPS == 50.0


def test_blank_and_special_frames_are_skipped() -> None:
    ppg = make_ppg({3: (4, 0.9), 6: (5, 0.8)}, frames=10)
    ppg[0] = [0, 1, 0, 0, 0, 0]  # <s>
    ppg[1] = [0, 0, 0, 1, 0, 0]  # <unk>

    assert decode_phones(ppg) == [(3, 4, np.float32(0.9)), (6, 5, np.float32(0.8))]


def test_repeated_frames_collapse_but_a_blank_separates_equal_tokens() -> None:
    ppg = make_ppg({2: (4, 0.9), 3: (4, 0.9), 4: (4, 0.9), 6: (4, 0.8)}, frames=8)

    phones = decode_phones(ppg)

    assert [(f, t) for f, t, _ in phones] == [(2, 4), (6, 4)]


def test_empty_ppg_decodes_to_nothing() -> None:
    assert decode_phones(np.zeros((0, N_CLASSES), dtype=np.float32)) == []


def test_phones_are_joined_per_word_using_absolute_window_start() -> None:
    # window bắt đầu ở 10.0 s; từ 0 = [10.0, 10.2) -> frame 0..10, từ 1 = [10.2, 10.4) -> 10..20
    ppg = make_ppg({2: (4, 0.9), 5: (5, 0.8), 14: (5, 0.95)}, frames=24)

    out = ipa_for_segment(ppg, 10.0, PPG_FPS, [(10.0, 10.2), (10.2, 10.4)], VOCAB)

    assert out == {0: "haɪ", 1: "aɪ"}


def test_boundary_phone_goes_to_the_nearer_word_within_tolerance() -> None:
    # từ 0 = frame [0, 10), từ 1 = frame [12, 22). Phone ở frame 10 nằm trong dung sai của cả hai
    # (cách từ 0 là 0, cách từ 1 là 2) -> gán cho từ 0; phone ở frame 12 nằm thật sự trong từ 1.
    ppg = make_ppg({4: (4, 0.9), 10: (5, 0.9), 12: (5, 0.9)}, frames=24)

    out = ipa_for_segment(ppg, 0.0, PPG_FPS, [(0.0, 0.2), (0.24, 0.44)], VOCAB)

    assert out == {0: "haɪ", 1: "aɪ"}


def test_phone_inside_tolerance_before_a_word_is_assigned_to_it() -> None:
    # từ duy nhất = frame [10, 20); phone ở frame 8 (đúng biên dung sai) được nhận, frame 7 không
    inside = make_ppg({8: (4, 0.9), 12: (5, 0.9)}, frames=24)
    outside = make_ppg({7: (4, 0.9), 12: (5, 0.9)}, frames=24)

    assert ipa_for_segment(inside, 0.0, PPG_FPS, [(0.2, 0.4)], VOCAB) == {0: "haɪ"}
    assert ipa_for_segment(outside, 0.0, PPG_FPS, [(0.2, 0.4)], VOCAB) == {0: "aɪ"}


def test_phone_strictly_inside_beats_a_neighbour_within_tolerance() -> None:
    # từ 0 = [0, 10), từ 1 = [10, 20): phone ở frame 10 nằm thật sự trong từ 1, dù cũng trong
    # dung sai của từ 0.
    ppg = make_ppg({10: (4, 0.9)}, frames=24)

    out = ipa_for_segment(ppg, 0.0, PPG_FPS, [(0.0, 0.2), (0.2, 0.4)], VOCAB)

    assert out == {1: "h"}


def test_low_probability_word_is_omitted_not_null() -> None:
    ppg = make_ppg({2: (4, 0.9), 14: (5, 0.5)}, frames=24)

    out = ipa_for_segment(ppg, 0.0, PPG_FPS, [(0.0, 0.2), (0.2, 0.4)], VOCAB)

    assert out == {0: "h"}
    assert 1 not in out


def test_confidence_is_the_mean_over_emitting_frames() -> None:
    # 0.9 và 0.6 -> trung bình 0.75 >= 0.7: giữ; 0.9 và 0.4 -> 0.65: ẩn
    keep = make_ppg({2: (4, 0.9), 6: (5, 0.6)}, frames=12)
    drop = make_ppg({2: (4, 0.9), 6: (5, 0.4)}, frames=12)

    assert ipa_for_segment(keep, 0.0, PPG_FPS, [(0.0, 0.24)], VOCAB) == {0: "haɪ"}
    assert ipa_for_segment(drop, 0.0, PPG_FPS, [(0.0, 0.24)], VOCAB) == {}


def test_word_without_any_phone_is_omitted() -> None:
    ppg = make_ppg({2: (4, 0.9)}, frames=40)

    out = ipa_for_segment(ppg, 0.0, PPG_FPS, [(0.0, 0.2), (0.5, 0.7)], VOCAB)

    assert out == {0: "h"}


def test_min_conf_and_tolerance_are_overridable() -> None:
    ppg = make_ppg({2: (4, 0.55)}, frames=12)

    assert ipa_for_segment(ppg, 0.0, PPG_FPS, [(0.0, 0.2)], VOCAB) == {}
    assert ipa_for_segment(ppg, 0.0, PPG_FPS, [(0.0, 0.2)], VOCAB, min_conf=0.5) == {0: "h"}


def test_stress_marks_are_never_produced() -> None:
    vocab = {**VOCAB, 4: "ˈh", 5: "ˌaɪ"}  # phòng khi vocab tương lai có dấu trọng âm
    ppg = make_ppg({2: (4, 0.9), 5: (5, 0.9)}, frames=12)

    out = ipa_for_segment(ppg, 0.0, PPG_FPS, [(0.0, 0.24)], vocab)

    assert out == {0: "haɪ"}
    assert not any(mark in text for text in out.values() for mark in "ˈˌ")


def test_token_missing_from_vocab_is_ignored() -> None:
    ppg = make_ppg({2: (4, 0.9), 5: (5, 0.9)}, frames=12)

    out = ipa_for_segment(ppg, 0.0, PPG_FPS, [(0.0, 0.24)], {0: "<pad>", 4: "h"})

    assert out == {0: "h"}


def test_ipa_module_has_no_text_to_phoneme_import() -> None:
    tree = ast.parse(Path(ipa.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint({"phonemizer", "g2p", "g2p_en", "espeakng", "epitran", "nltk"})
