"use client";

import { useActorRef, useSelector } from "@xstate/react";
import { useEffect, useMemo, useRef, useState } from "react";
import type {
  AppSettings,
  Lesson,
  LessonProgress,
} from "@shadowenglab/contracts";
import { PlayerControls } from "@/components/PlayerControls";
import { PracticeHeader } from "@/components/PracticeHeader";
import { TranscriptList } from "@/components/TranscriptList";
import { VideoPane } from "@/components/VideoPane";
import { makePlaySample, type PlayableLesson } from "@/lib/player/playRange";
import { playerMachine, type RepeatCount } from "@/lib/player/playerMachine";
import { useLesson, useLessonProgress, useSettings } from "@/lib/queries";

type SessionDefaults = Pick<
  AppSettings,
  "playbackRate" | "repeat" | "recordFactor"
>;

/** Mặc định khi GET /settings lỗi (UI-SPEC E7): 1x, ×1, +50%. */
const DEFAULT_SETTINGS: SessionDefaults = {
  playbackRate: 1,
  repeat: 1,
  recordFactor: 1.5,
};

const RATE_OPTIONS = [0.75, 1] as const;
const RECORD_FACTOR_OPTIONS = [1.25, 1.5, 2] as const;

function nearest(options: readonly number[], value: number): number {
  return options.reduce((best, option) =>
    Math.abs(option - value) < Math.abs(best - value) ? option : best,
  );
}

/** Đưa giá trị đã lưu về đúng các lựa chọn của thanh điều khiển. */
function sessionDefaults(settings: SessionDefaults): {
  rate: number;
  repeat: RepeatCount;
  recordFactor: number;
} {
  return {
    rate: nearest(RATE_OPTIONS, settings.playbackRate),
    repeat: settings.repeat,
    recordFactor: nearest(RECORD_FACTOR_OPTIONS, settings.recordFactor),
  };
}

function segmentDurationsMs(lesson: Lesson): number[] {
  return lesson.segments.map((segment) =>
    Math.round((segment.end - segment.start) * 1000 + segment.endExtraMs),
  );
}

interface PracticeRoomProps {
  lessonId: string;
}

export function PracticeRoom({ lessonId }: PracticeRoomProps) {
  const lesson = useLesson(lessonId);
  const progress = useLessonProgress(lessonId);
  const settings = useSettings();

  if (lesson.isError) {
    return <p role="alert">{lesson.error.message}</p>;
  }
  if (lesson.isPending || progress.isPending || settings.isPending) {
    return <p>Đang tải…</p>;
  }

  return (
    <LoadedRoom
      lesson={lesson.data}
      progress={progress.data}
      settings={settings.data}
    />
  );
}

interface LoadedRoomProps {
  lesson: Lesson;
  /** undefined khi GET /progress lỗi: vẫn luyện được, chỉ mất dấu "đã tập". */
  progress: LessonProgress | undefined;
  /** undefined khi GET /settings lỗi: dùng mặc định tích hợp. */
  settings: AppSettings | undefined;
}

function LoadedRoom({ lesson, progress, settings }: LoadedRoomProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const lessonRef = useRef<PlayableLesson>(lesson);
  useEffect(() => {
    lessonRef.current = lesson;
  }, [lesson]);

  // Machine tạo một lần: actor playSample đọc video/bài qua ref nên luôn thấy dữ liệu mới nhất.
  // Actor ghi âm và tải lên do 02-14 cung cấp qua `provide`.
  const [machine] = useState(() =>
    playerMachine.provide({
      actors: {
        playSample: makePlaySample(
          () => videoRef.current,
          () => lessonRef.current,
        ),
      },
    }),
  );

  const defaults = sessionDefaults(settings ?? DEFAULT_SETTINGS);
  const actorRef = useActorRef(machine, {
    input: {
      segmentCount: lesson.segments.length,
      startIndex: progress?.firstUnpracticedIndex ?? 0,
      segmentDurationsMs: segmentDurationsMs(lesson),
      repeat: defaults.repeat,
      rate: defaults.rate,
      recordFactor: defaults.recordFactor,
    },
  });
  const snapshot = useSelector(actorRef, (state) => state);
  const [videoReady, setVideoReady] = useState(false);

  const practiced = useMemo(
    () =>
      new Set(
        (progress?.segments ?? [])
          .filter((item) => item.voicedAttempts >= 1)
          .map((item) => item.segmentIndex),
      ),
    [progress],
  );

  const { context } = snapshot;
  const index = context.segmentIndex;
  const segment = lesson.segments[index];
  if (!segment) return null;

  return (
    <div className="flex h-screen flex-col">
      <PracticeHeader
        title={lesson.title}
        total={lesson.segments.length}
        currentIndex={index}
        practiced={practiced}
      />
      <div className="flex min-h-0 flex-1 flex-wrap items-stretch overflow-y-auto min-[1160px]:flex-nowrap min-[1160px]:overflow-hidden">
        <aside
          aria-label="Video và transcript"
          className="flex min-w-[520px] flex-[0_1_600px] flex-col border-r border-border bg-[color:var(--slate-2)] min-[1160px]:min-h-0"
        >
          <VideoPane
            lessonId={lesson.id}
            videoRef={videoRef}
            startSec={segment.start}
            endSec={segment.end}
            sentenceNumber={index + 1}
            onReadyChange={setVideoReady}
          />
          <PlayerControls
            stateValue={snapshot.value}
            segmentIndex={index}
            segmentCount={context.segmentCount}
            rate={context.rate}
            repeat={context.repeat}
            recordFactor={context.recordFactor}
            videoReady={videoReady}
            send={actorRef.send}
          />
          <TranscriptList
            segments={lesson.segments}
            currentIndex={index}
            practiced={practiced}
            onSelect={(next) => actorRef.send({ type: "GOTO", index: next })}
          />
        </aside>
        <main className="flex min-w-0 flex-[999_1_560px] flex-col gap-8 px-12 pb-10 pt-9 min-[1160px]:overflow-y-auto">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px] text-muted-foreground">
            <span className="font-bold text-foreground">Câu {index + 1}</span>
          </div>
          <p className="m-0 text-[38px] font-semibold leading-[1.2] tracking-[-0.015em]">
            {segment.text}
          </p>
        </main>
      </div>
    </div>
  );
}
