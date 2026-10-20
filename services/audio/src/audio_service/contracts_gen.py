# GENERATED từ packages/contracts/schema/contracts.schema.json — không sửa tay (chạy make contracts)

from __future__ import annotations

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, RootModel
from typing_extensions import TypeAliasType


class Word(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    i: Annotated[int, Field(ge=0, le=9007199254740991)]
    text: str
    start: Annotated[float, Field(ge=0.0)]
    end: Annotated[float, Field(ge=0.0)]
    asr_prob: Annotated[float, Field(alias="asrProb", ge=0.0, le=1.0)]
    ipa: str | None = None
    ref_confidence: Annotated[float | None, Field(alias="refConfidence", ge=0.0, le=1.0)] = None
    prominence: float | None = None


class TimeRange(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    start: Annotated[float, Field(ge=0.0)]
    end: Annotated[float, Field(ge=0.0)]


class LessonError(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    step: str
    message: str


class AudioQuality(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    label: Literal["clean", "music"]
    non_vocal_ratio: Annotated[float, Field(alias="nonVocalRatio", ge=0.0)]


TimingMsAdditionalProperty = TypeAliasType(
    "TimingMsAdditionalProperty", Annotated[float, Field(ge=0.0)]
)


class Versions(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    scorer: str
    thresholds: str


class Sound(RootModel[float]):
    root: Annotated[float, Field(ge=0.0, le=1.0)]


class Scores(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    overall: Annotated[float, Field(ge=0.0, le=1.0)]
    sound: Sound | None
    intonation: Annotated[float, Field(ge=0.0, le=1.0)]
    rhythm: Annotated[float, Field(ge=0.0, le=1.0)]


class WordScore(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    text: str
    status: Literal["scored", "missing", "ref_unclear"]
    similarity: Annotated[float, Field(ge=0.0, le=1.0)]
    start: Annotated[float, Field(ge=0.0)]
    end: Annotated[float, Field(ge=0.0)]
    ref_phones: Annotated[str | None, Field(alias="refPhones")] = None
    user_phones: Annotated[str | None, Field(alias="userPhones")] = None


class WordBound(RootModel[int]):
    root: Annotated[int, Field(ge=0, le=9007199254740991)]


class Contour(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    ref: list[float | None]
    user: list[float | None]
    word_bounds: Annotated[list[WordBound], Field(alias="wordBounds")]


class StressEntry(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    word: str
    ref: float
    user: float


class PauseEntry(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    after_word: Annotated[int, Field(alias="afterWord", ge=0, le=9007199254740991)]
    ref_ms: Annotated[int, Field(alias="refMs", ge=0, le=9007199254740991)]
    user_ms: Annotated[int, Field(alias="userMs", ge=0, le=9007199254740991)]


class StressMismatchData(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    ref_word: Annotated[str, Field(alias="refWord")]
    user_word: Annotated[str, Field(alias="userWord")]


class ExtraPauseData(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    ref_ms: Annotated[int, Field(alias="refMs", ge=0, le=9007199254740991)]
    user_ms: Annotated[int, Field(alias="userMs", ge=0, le=9007199254740991)]


class FinalContourData(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    ref_slope: Annotated[float, Field(alias="refSlope")]
    user_slope: Annotated[float, Field(alias="userSlope")]


class FlatPitchData(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    pitch_range: Annotated[float, Field(alias="pitchRange", ge=0.0, le=1.0)]


class PitchDeviationData(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    mean_diff_st: Annotated[float, Field(alias="meanDiffSt")]


class PhoneData(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    ref_phones: Annotated[str, Field(alias="refPhones")]
    user_phones: Annotated[str, Field(alias="userPhones")]
    similarity: Annotated[float, Field(ge=0.0, le=1.0)]


class WordMissingData(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )


class Tip(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    text: str
    issue_ref: Annotated[int, Field(alias="issueRef", ge=0, le=9007199254740991)]
    source: Literal["template", "llm"]


class IssueCode(
    RootModel[
        Literal[
            "STRESS_MISMATCH",
            "EXTRA_PAUSE",
            "FINAL_CONTOUR",
            "FLAT_PITCH",
            "PITCH_DEVIATION",
            "PHONE",
            "WORD_MISSING",
        ]
    ]
):
    root: Literal[
        "STRESS_MISMATCH",
        "EXTRA_PAUSE",
        "FINAL_CONTOUR",
        "FLAT_PITCH",
        "PITCH_DEVIATION",
        "PHONE",
        "WORD_MISSING",
    ]


class ClipWord(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    i: Annotated[int, Field(ge=0, le=9007199254740991)]
    text: str


class WordFlags(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    word_index: Annotated[int, Field(alias="wordIndex", ge=0, le=9007199254740991)]
    flags: list[Literal["sound", "stress", "pitch", "pause", "speed"]]


class ErrorType(
    RootModel[
        Literal[
            "wrong_stress",
            "flat",
            "extra_pause",
            "final_rise",
            "pitch_off",
            "weak_form",
            "final_drop",
        ]
    ]
):
    root: Literal[
        "wrong_stress", "flat", "extra_pause", "final_rise", "pitch_off", "weak_form", "final_drop"
    ]


class EvalAlsoPresent(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    error_type: Annotated[ErrorType, Field(alias="errorType")]
    word_index: Annotated[int | None, Field(alias="wordIndex", ge=0, le=9007199254740991)] = None


class AttemptAck(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    lesson_id: Annotated[str, Field(alias="lessonId")]
    segment_index: Annotated[int, Field(alias="segmentIndex", ge=0, le=9007199254740991)]
    attempt: Annotated[int, Field(ge=1, le=9007199254740991)]
    duration_ms: Annotated[int, Field(alias="durationMs", ge=0, le=9007199254740991)]
    voiced: bool
    saved_for_eval: Annotated[bool, Field(alias="savedForEval")]


class AttemptSummary(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    attempt: Annotated[int, Field(ge=1, le=9007199254740991)]
    overall: Annotated[float, Field(ge=0.0, le=1.0)]
    created_at: Annotated[str, Field(alias="createdAt")]


class AppSettings(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    playback_rate: Annotated[float, Field(alias="playbackRate", ge=0.5, le=1.0)]
    repeat: Literal[1, 2, 3]
    record_factor: Annotated[float, Field(alias="recordFactor", ge=1.0, le=2.0)]
    data_dir: Annotated[str, Field(alias="dataDir")]
    accent: Literal["US"]


class VideoPreview(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    video_id: Annotated[str, Field(alias="videoId")]
    title: str
    duration_sec: Annotated[float, Field(alias="durationSec", ge=0.0)]
    channel: str | None = None
    thumbnail_url: Annotated[str | None, Field(alias="thumbnailUrl")] = None
    existing_lesson_id: Annotated[str | None, Field(alias="existingLessonId")] = None


class CreateLessonRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    url: str
    start: Annotated[float | None, Field(ge=0.0)] = None
    end: Annotated[float | None, Field(ge=0.0)] = None


class FirstUnpracticedIndex(RootModel[int]):
    root: Annotated[int, Field(ge=0, le=9007199254740991)]


class LessonSummary(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: str
    video_id: Annotated[str, Field(alias="videoId")]
    title: str
    duration_sec: Annotated[float, Field(alias="durationSec", ge=0.0)]
    thumbnail_url: Annotated[str | None, Field(alias="thumbnailUrl")] = None
    range: TimeRange
    pad_ms: Annotated[int, Field(alias="padMs", ge=0, le=9007199254740991)] = 150
    status: Literal[
        "queued",
        "downloading",
        "separating",
        "transcribing",
        "segmenting",
        "analyzing",
        "ready",
        "failed",
    ]
    error: LessonError | None = None
    audio_quality: Annotated[AudioQuality | None, Field(alias="audioQuality")] = None
    created_at: Annotated[str, Field(alias="createdAt")]


class SegmentProgress(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    segment_index: Annotated[int, Field(alias="segmentIndex", ge=0, le=9007199254740991)]
    attempts: Annotated[int, Field(ge=0, le=9007199254740991)]
    voiced_attempts: Annotated[int, Field(alias="voicedAttempts", ge=0, le=9007199254740991)]
    best_overall: Annotated[float | None, Field(alias="bestOverall", ge=0.0, le=1.0)] = None
    best_attempt: Annotated[int | None, Field(alias="bestAttempt", ge=1, le=9007199254740991)] = (
        None
    )


class ModelStatuses(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    demucs: Literal["missing", "loading", "ready"]
    whisper: Literal["missing", "loading", "ready"]
    wav2vec2: Literal["missing", "loading", "ready"]


class OpenAiKeyCheckRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    api_key: Annotated[str | None, Field(alias="apiKey")] = None


class OpenAiKeyCheckResult(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    valid: bool | None
    saved: bool
    masked_key: Annotated[str | None, Field(alias="maskedKey")] = None
    reason: Literal["invalid", "network", "no_key"] | None = None


class UpdateSegmentTextRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    text: Annotated[str, Field(max_length=500, min_length=1)]


class ApiError(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    code: Literal[
        "invalid_request",
        "invalid_url",
        "channel_url",
        "video_unavailable",
        "live_video",
        "invalid_range",
        "duplicate_lesson",
        "not_found",
        "invalid_state",
        "invalid_segment",
        "unsupported_media",
        "payload_too_large",
        "recording_too_long",
        "no_speech",
        "busy",
        "no_openai_key",
        "upstream_error",
        "network_error",
        "invalid_settings",
        "forbidden_origin",
        "internal_error",
    ]
    message: str
    lesson_id: Annotated[str | None, Field(alias="lessonId")] = None


class Segment(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    index: Annotated[int, Field(ge=0, le=9007199254740991)]
    text: str
    start: Annotated[float, Field(ge=0.0)]
    end: Annotated[float, Field(ge=0.0)]
    end_extra_ms: Annotated[int, Field(alias="endExtraMs", ge=0, le=9007199254740991)] = 0
    words: list[Word]
    translation: str | None = None


class Lesson(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: str
    video_id: Annotated[str, Field(alias="videoId")]
    title: str
    duration_sec: Annotated[float, Field(alias="durationSec", ge=0.0)]
    thumbnail_url: Annotated[str | None, Field(alias="thumbnailUrl")] = None
    range: TimeRange
    pad_ms: Annotated[int, Field(alias="padMs", ge=0, le=9007199254740991)] = 150
    status: Literal[
        "queued",
        "downloading",
        "separating",
        "transcribing",
        "segmenting",
        "analyzing",
        "ready",
        "failed",
    ]
    error: LessonError | None = None
    audio_quality: Annotated[AudioQuality | None, Field(alias="audioQuality")] = None
    segments: list[Segment]
    created_at: Annotated[str, Field(alias="createdAt")]


class Prosody(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    speed: Annotated[float, Field(ge=0.0, le=1.0)]
    pitch_range: Annotated[float, Field(alias="pitchRange", ge=0.0, le=1.0)]
    melody_match: Annotated[float, Field(alias="melodyMatch", ge=0.0, le=1.0)]
    contour: Contour
    stress: list[StressEntry]
    pauses: list[PauseEntry]


class StressMismatchIssue(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    code: Literal["STRESS_MISMATCH"]
    word_index: Annotated[int, Field(alias="wordIndex", ge=0, le=9007199254740991)]
    data: StressMismatchData


class ExtraPauseIssue(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    code: Literal["EXTRA_PAUSE"]
    word_index: Annotated[int, Field(alias="wordIndex", ge=0, le=9007199254740991)]
    data: ExtraPauseData


class FinalContourIssue(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    code: Literal["FINAL_CONTOUR"]
    data: FinalContourData


class FlatPitchIssue(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    code: Literal["FLAT_PITCH"]
    data: FlatPitchData


class PitchDeviationIssue(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    code: Literal["PITCH_DEVIATION"]
    word_index: Annotated[int, Field(alias="wordIndex", ge=0, le=9007199254740991)]
    data: PitchDeviationData


class PhoneIssue(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    code: Literal["PHONE"]
    word_index: Annotated[int, Field(alias="wordIndex", ge=0, le=9007199254740991)]
    data: PhoneData


class WordMissingIssue(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    code: Literal["WORD_MISSING"]
    word_index: Annotated[int, Field(alias="wordIndex", ge=0, le=9007199254740991)]
    data: WordMissingData


class ClipManifest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    clip_id: Annotated[str, Field(alias="clipId")]
    video_id: Annotated[str, Field(alias="videoId")]
    sentence_text: Annotated[str, Field(alias="sentenceText")]
    words: list[ClipWord]
    ref_audio: Annotated[str, Field(alias="refAudio")]
    user_audio: Annotated[str, Field(alias="userAudio")]
    gold: Literal["none", "identical", "wrong"] = "none"
    system_score: Annotated[float | None, Field(alias="systemScore", ge=0.0, le=1.0)] = None


class Label(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    clip_id: Annotated[str, Field(alias="clipId")]
    rater_id: Annotated[str, Field(alias="raterId")]
    overall: Literal[1, 2, 3, 4, 5]
    word_flags: Annotated[list[WordFlags], Field(alias="wordFlags")]
    final_contour_match: Annotated[bool, Field(alias="finalContourMatch")]
    unsure: bool
    note: str | None = None
    duration_ms: Annotated[int, Field(alias="durationMs", ge=0, le=9007199254740991)]
    created_at: Annotated[str, Field(alias="createdAt")]


class EvalCase(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    case_id: Annotated[str, Field(alias="caseId", min_length=1)]
    lesson_id: Annotated[str, Field(alias="lessonId")]
    segment_index: Annotated[int, Field(alias="segmentIndex", ge=0, le=9007199254740991)]
    seg_start_ms: Annotated[int, Field(alias="segStartMs", ge=0, le=9007199254740991)]
    seg_end_ms: Annotated[int, Field(alias="segEndMs", ge=0, le=9007199254740991)]
    seg_end_extra_ms: Annotated[int, Field(alias="segEndExtraMs", ge=0, le=9007199254740991)]
    seg_text_hash: Annotated[str, Field(alias="segTextHash", max_length=16, min_length=16)]
    kind: Literal["error", "correct"]
    error_type: Annotated[ErrorType | None, Field(alias="errorType")] = None
    word_index: Annotated[int | None, Field(alias="wordIndex", ge=0, le=9007199254740991)] = None
    also_present: Annotated[list[EvalAlsoPresent] | None, Field(alias="alsoPresent")] = None
    split: Literal["tuning", "heldout"] | None = None
    clip: str | None = None
    note: str | None = None


class LessonListItem(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    lesson: LessonSummary
    segment_count: Annotated[int, Field(alias="segmentCount", ge=0, le=9007199254740991)]
    practiced_count: Annotated[int, Field(alias="practicedCount", ge=0, le=9007199254740991)]
    first_unpracticed_index: Annotated[
        FirstUnpracticedIndex | None, Field(alias="firstUnpracticedIndex")
    ]


class LessonProgress(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    lesson_id: Annotated[str, Field(alias="lessonId")]
    segments: list[SegmentProgress]
    first_unpracticed_index: Annotated[
        FirstUnpracticedIndex | None, Field(alias="firstUnpracticedIndex")
    ]


class SystemStatus(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    models: ModelStatuses
    has_key: Annotated[bool, Field(alias="hasKey")]
    masked_key: Annotated[str | None, Field(alias="maskedKey")] = None
    active_data_dir: Annotated[str, Field(alias="activeDataDir")]


class Issue(
    RootModel[
        StressMismatchIssue
        | ExtraPauseIssue
        | FinalContourIssue
        | FlatPitchIssue
        | PitchDeviationIssue
        | PhoneIssue
        | WordMissingIssue
    ]
):
    root: (
        StressMismatchIssue
        | ExtraPauseIssue
        | FinalContourIssue
        | FlatPitchIssue
        | PitchDeviationIssue
        | PhoneIssue
        | WordMissingIssue
    )


class ScoreResult(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    lesson_id: Annotated[str, Field(alias="lessonId")]
    segment_index: Annotated[int, Field(alias="segmentIndex", ge=0, le=9007199254740991)]
    attempt: Annotated[int, Field(ge=1, le=9007199254740991)]
    mode: Literal["full", "intonationOnly"]
    versions: Versions
    timing_ms: Annotated[dict[str, TimingMsAdditionalProperty], Field(alias="timingMs")]
    scores: Scores
    words: list[WordScore]
    prosody: Prosody
    issues: list[Issue]
    tips: list[Tip]
