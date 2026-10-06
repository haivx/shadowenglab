"""Test cho split_sentences: tách câu theo dấu câu, khoảng lặng, độ dài và gộp mảnh ngắn."""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence

import pytest

from audio_service.lesson.segment import (
    HARD_GAP_S,
    MAX_DUR_S,
    MAX_MERGED_S,
    MAX_WORDS,
    MIN_DUR_S,
    AsrWord,
    split_sentences,
)


def make_words(
    texts: Sequence[str],
    *,
    dur: float | Sequence[float] = 0.8,
    gap: float = 0.05,
    gaps: Mapping[int, float] | None = None,
    start: float = 0.0,
) -> list[AsrWord]:
    """Dựng danh sách từ giả. `gaps[i]` là khoảng lặng sau từ thứ i (mặc định `gap`)."""
    out: list[AsrWord] = []
    t = start
    for i, text in enumerate(texts):
        d = dur[i] if not isinstance(dur, float | int) else float(dur)
        out.append(AsrWord(text=text, start=t, end=t + d, probability=0.9))
        t += d + (gaps or {}).get(i, gap)
    return out


def span_dur(words: Sequence[AsrWord], span: tuple[int, int]) -> float:
    a, b = span
    return words[b - 1].end - words[a].start


def test_constants_match_plan() -> None:
    assert HARD_GAP_S == 0.7
    assert MAX_DUR_S == 8.0
    assert MAX_WORDS == 15
    assert MIN_DUR_S == 1.5
    assert MAX_MERGED_S == 9.0


def test_empty_returns_empty() -> None:
    assert split_sentences([]) == []


def test_single_word_is_one_span() -> None:
    assert split_sentences(make_words([" Hello"])) == [(0, 1)]


def test_splits_after_sentence_punctuation() -> None:
    words = make_words(
        [" Hello", " there.", " How", " are", " you?"],
        gaps={1: 0.2},
    )
    assert split_sentences(words) == [(0, 2), (2, 5)]


@pytest.mark.parametrize("closer", ['"', "'", ")", "]", "”", "’"])
def test_closing_quote_or_bracket_after_punctuation_still_ends_sentence(closer: str) -> None:
    words = make_words(
        [" He", " said", f" no.{closer}", " Then", " he", " left"],
        gaps={2: 0.2},
    )
    assert split_sentences(words) == [(0, 3), (3, 6)]


def test_exclamation_ends_sentence() -> None:
    words = make_words([" Stop", " it!", " Please", " do"], gaps={1: 0.2})
    assert split_sentences(words) == [(0, 2), (2, 4)]


def test_splits_at_hard_gap_without_punctuation() -> None:
    words = make_words([" alpha", " beta"], dur=1.6, gaps={0: 0.75})
    assert split_sentences(words) == [(0, 1), (1, 2)]


def test_gap_just_below_hard_gap_does_not_split() -> None:
    words = make_words([" alpha", " beta"], dur=1.6, gaps={0: 0.65})
    assert split_sentences(words) == [(0, 2)]


def test_long_run_splits_right_after_comma_near_middle() -> None:
    texts = [f" w{i}" for i in range(20)]
    texts[8] = " w8,"
    words = make_words(texts, dur=0.45)
    assert span_dur(words, (0, 20)) > MAX_DUR_S
    spans = split_sentences(words)
    assert spans == [(0, 9), (9, 20)]
    assert all(span_dur(words, s) >= MIN_DUR_S for s in spans)


def test_comma_too_close_to_edge_is_skipped() -> None:
    texts = [f" w{i}" for i in range(20)]
    texts[1] = " w1,"  # trái chỉ ~0.95 s, không hợp lệ
    texts[12] = " w12,"
    words = make_words(texts, dur=0.45)
    assert split_sentences(words) == [(0, 13), (13, 20)]


def test_closest_to_half_comma_wins() -> None:
    texts = [f" w{i}" for i in range(20)]
    texts[4] = " w4,"
    texts[9] = " w9,"
    words = make_words(texts, dur=0.45)
    assert split_sentences(words) == [(0, 10), (10, 20)]


def test_long_run_without_comma_splits_at_pause() -> None:
    words = make_words([f" w{i}" for i in range(20)], dur=0.45, gaps={11: 0.3})
    assert split_sentences(words) == [(0, 12), (12, 20)]


def test_long_run_without_comma_or_pause_splits_at_largest_gap() -> None:
    words = make_words(
        [f" w{i}" for i in range(20)],
        dur=0.45,
        gaps={5: 0.15, 13: 0.2},
    )
    assert split_sentences(words) == [(0, 14), (14, 20)]


def test_many_words_within_duration_still_split_by_word_count() -> None:
    texts = [f" w{i}" for i in range(18)]
    texts[8] = " w8,"
    words = make_words(texts, dur=0.2, gap=0.05)  # 4.45 s nhưng 18 > MAX_WORDS
    assert span_dur(words, (0, 18)) < MAX_DUR_S
    assert split_sentences(words) == [(0, 9), (9, 18)]


def test_very_long_run_is_split_recursively() -> None:
    words = make_words([f" w{i}" for i in range(60)], dur=0.45)
    spans = split_sentences(words)
    assert len(spans) >= 3
    assert all(b - a <= MAX_WORDS for a, b in spans)
    assert all(span_dur(words, s) <= MAX_DUR_S for s in spans)


def test_short_fragment_merges_into_neighbour_with_smaller_gap_next() -> None:
    words = make_words(
        [" One", " two", " three.", " Yes.", " Four", " five", " six."],
        dur=[1.0, 1.0, 1.0, 0.9, 1.0, 1.0, 1.0],
        gaps={2: 0.5, 3: 0.2},
    )
    assert split_sentences(words) == [(0, 3), (3, 7)]


def test_short_fragment_merges_into_neighbour_with_smaller_gap_previous() -> None:
    words = make_words(
        [" One", " two", " three.", " Yes.", " Four", " five", " six."],
        dur=[1.0, 1.0, 1.0, 0.9, 1.0, 1.0, 1.0],
        gaps={2: 0.2, 3: 0.5},
    )
    assert split_sentences(words) == [(0, 4), (4, 7)]


def test_short_fragment_merged_when_result_at_most_max_merged() -> None:
    words = make_words(
        [" a", " b", " c", " d.", " Yes."],
        dur=[1.95, 1.95, 1.95, 1.95, 0.8],
        gaps={3: 0.1},
    )
    assert span_dur(words, (0, 4)) <= MAX_DUR_S
    assert split_sentences(words) == [(0, 5)]


def test_short_fragment_left_alone_when_merge_would_exceed_max_merged() -> None:
    words = make_words(
        [" a", " b", " c", " d.", " Yes."],
        dur=[1.95, 1.95, 1.95, 1.95, 0.9],
        gaps={3: 0.3},
    )
    assert span_dur(words, (0, 4)) <= MAX_DUR_S
    assert span_dur(words, (0, 5)) > MAX_MERGED_S
    assert split_sentences(words) == [(0, 4), (4, 5)]


def test_consecutive_tiny_sentences_cascade_into_one_span() -> None:
    words = make_words([" A.", " B.", " C."], dur=0.5, gap=0.1)
    assert split_sentences(words) == [(0, 3)]


def test_does_not_mutate_input() -> None:
    words = make_words([" Hello", " there.", " How", " are", " you?"], gaps={1: 0.2})
    snapshot = list(words)
    split_sentences(words)
    assert words == snapshot


def _random_words(rng: random.Random) -> list[AsrWord]:
    n = rng.randint(1, 80)
    t = 0.0
    out: list[AsrWord] = []
    for i in range(n):
        d = rng.uniform(0.1, 0.9)
        text = f" w{i}"
        r = rng.random()
        if r < 0.1:
            text += "."
        elif r < 0.2:
            text += ","
        elif r < 0.25:
            text += "?"
        out.append(AsrWord(text=text, start=t, end=t + d, probability=rng.random()))
        t += d + rng.choice([0.0, 0.02, 0.1, 0.3, 0.8, 1.2])
    return out


@pytest.mark.parametrize("seed", range(60))
def test_property_spans_cover_every_word_exactly_once(seed: int) -> None:
    words = _random_words(random.Random(seed))
    spans = split_sentences(words)

    assert spans, "danh sách từ không rỗng phải cho ít nhất một span"
    assert spans[0][0] == 0
    assert spans[-1][1] == len(words)
    for (_a, b), (c, _d) in zip(spans, spans[1:], strict=False):
        assert b == c  # liền kề, không chồng lấn, không hở
    assert all(a < b for a, b in spans)  # không span rỗng
    starts = [words[a].start for a, _ in spans]
    assert all(x < y for x, y in zip(starts, starts[1:], strict=False))
    ends = [words[b - 1].end for _, b in spans]
    assert all(x < y for x, y in zip(ends, ends[1:], strict=False))
