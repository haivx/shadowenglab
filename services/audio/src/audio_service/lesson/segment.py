"""Tách câu từ danh sách từ của Whisper (product.md M1). Hàm thuần, không IO.

Đầu ra là các span nửa mở `(start_index, end_index)` trên danh sách từ, không phải model
contract, để module này độc lập với contract sinh tự động; bước dựng bài đổi span thành `Segment`.

Các ngưỡng là giá trị khởi đầu (RESEARCH A1), sẽ chỉnh trên video thật. Hạn chế đã biết: từ
viết tắt kết thúc bằng dấu chấm ("Dr.", "Mr.") bị coi là hết câu; mảnh quá ngắn sinh ra từ đó
được bước gộp xử lý khi có thể.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

SENTENCE_END = (".", "?", "!")
CLAUSE_END = (",", ";", ":")
_CLOSERS = "\"')]}”’»"

HARD_GAP_S = 0.7
SOFT_GAP_S = 0.25
MAX_DUR_S = 8.0
MAX_WORDS = 15
MIN_DUR_S = 1.5
MAX_MERGED_S = 9.0


@dataclass(frozen=True, slots=True)
class AsrWord:
    """Một từ do Whisper trả về; `text` giữ nguyên khoảng trắng đầu của Whisper."""

    text: str
    start: float
    end: float
    probability: float


Span = tuple[int, int]


def _core(text: str) -> str:
    """Bỏ khoảng trắng và dấu ngoặc/nháy đóng ở cuối để nhìn thấy dấu câu thật."""
    return text.rstrip().rstrip(_CLOSERS)


def _ends_sentence(word: AsrWord) -> bool:
    return _core(word.text).endswith(SENTENCE_END)


def _ends_clause(word: AsrWord) -> bool:
    return _core(word.text).endswith(CLAUSE_END)


def _gap(words: Sequence[AsrWord], k: int) -> float:
    """Khoảng lặng giữa từ k-1 và từ k."""
    return words[k].start - words[k - 1].end


def _dur(words: Sequence[AsrWord], span: Span) -> float:
    a, b = span
    return words[b - 1].end - words[a].start


def _initial_chunks(words: Sequence[AsrWord]) -> list[Span]:
    chunks: list[Span] = []
    begin = 0
    for k in range(1, len(words)):
        if _ends_sentence(words[k - 1]) or _gap(words, k) >= HARD_GAP_S:
            chunks.append((begin, k))
            begin = k
    chunks.append((begin, len(words)))
    return chunks


def _too_long(words: Sequence[AsrWord], span: Span) -> bool:
    return _dur(words, span) > MAX_DUR_S or span[1] - span[0] > MAX_WORDS


def _choose_cut(words: Sequence[AsrWord], span: Span) -> int:
    """Chọn vị trí cắt k (trái = [a, k), phải = [k, b)) cho span dài, a < k < b."""
    a, b = span
    half = _dur(words, span) / 2
    positions = range(a + 1, b)

    def valid(k: int) -> bool:
        return _dur(words, (a, k)) >= MIN_DUR_S and _dur(words, (k, b)) >= MIN_DUR_S

    def off_center(k: int) -> float:
        return abs(_dur(words, (a, k)) - half)

    tiers = (
        [k for k in positions if _ends_clause(words[k - 1])],
        [k for k in positions if _gap(words, k) >= SOFT_GAP_S],
    )
    for tier in tiers:
        candidates = [k for k in tier if valid(k)]
        if candidates:
            return min(candidates, key=off_center)

    # Không có dấu phẩy hay khoảng lặng hợp lệ: lấy khoảng lặng lớn nhất, ưu tiên hai nửa
    # đều đủ dài, hoà thì lấy vị trí gần giữa nhất.
    pool = [k for k in positions if valid(k)] or list(positions)
    return min(pool, key=lambda k: (-_gap(words, k), off_center(k)))


def _split_long(words: Sequence[AsrWord], span: Span) -> list[Span]:
    if span[1] - span[0] < 2 or not _too_long(words, span):
        return [span]
    k = _choose_cut(words, span)
    return _split_long(words, (span[0], k)) + _split_long(words, (k, span[1]))


def _merge_short(words: Sequence[AsrWord], chunks: list[Span]) -> list[Span]:
    chunks = list(chunks)
    while True:
        for i, span in enumerate(chunks):
            if len(chunks) < 2 or _dur(words, span) >= MIN_DUR_S:
                continue
            prev_gap = _gap(words, span[0]) if i > 0 else None
            next_gap = _gap(words, span[1]) if i < len(chunks) - 1 else None
            if prev_gap is not None and (next_gap is None or prev_gap <= next_gap):
                merged = (chunks[i - 1][0], span[1])
                target = i - 1
            elif next_gap is not None:
                merged = (span[0], chunks[i + 1][1])
                target = i
            else:
                continue
            if _dur(words, merged) > MAX_MERGED_S:
                continue
            chunks[target : target + 2] = [merged]
            break
        else:
            return chunks


def split_sentences(words: Sequence[AsrWord]) -> list[tuple[int, int]]:
    """Chia từ thành các span nửa mở liền kề, phủ mỗi từ đúng một lần.

    1. Cắt sau từ kết thúc bằng `.?!` (kể cả khi theo sau là nháy/ngoặc đóng) hoặc khi
       khoảng lặng tới từ kế >= HARD_GAP_S.
    2. Span dài hơn MAX_DUR_S hoặc MAX_WORDS được cắt đệ quy tại dấu phẩy, nếu không có thì
       tại khoảng lặng >= SOFT_GAP_S, nếu không có thì tại khoảng lặng lớn nhất; chọn điểm
       gần giữa nhất và ưu tiên hai nửa đều >= MIN_DUR_S.
    3. Span ngắn hơn MIN_DUR_S được gộp vào hàng xóm có khoảng lặng nhỏ hơn nếu kết quả
       <= MAX_MERGED_S.
    """
    if not words:
        return []
    chunks: list[Span] = []
    for chunk in _initial_chunks(words):
        chunks.extend(_split_long(words, chunk))
    return _merge_short(words, chunks)
