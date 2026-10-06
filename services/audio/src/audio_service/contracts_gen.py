# GENERATED từ packages/contracts/schema/contracts.schema.json — không sửa tay (chạy make contracts)

from __future__ import annotations

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


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
