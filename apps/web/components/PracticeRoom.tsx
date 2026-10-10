"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useActorRef, useSelector } from "@xstate/react";
import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";
import { fromPromise } from "xstate";
import type {
  AppSettings,
  Lesson,
  LessonProgress,
  ScoreResult,
} from "@shadowenglab/contracts";
import { AttemptStrip } from "@/components/AttemptStrip";
import { PlayerControls } from "@/components/PlayerControls";
import { BackToLibraryLink, PracticeHeader } from "@/components/PracticeHeader";
import { ResultActionBar } from "@/components/ResultActionBar";
import { ResultPanel } from "@/components/ResultPanel";
import {
  MetricSkeleton,
  SentenceStatePanel,
} from "@/components/SentenceStatePanel";
import { SpokenIpa } from "@/components/SpokenIpa";
import {
  TranscriptList,
  TranscriptListSkeleton,
  useTranslationTool,
} from "@/components/TranscriptList";
import { VideoPane } from "@/components/VideoPane";
import {
  Alert,
  AlertAction,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { uploadAttempt } from "@/lib/api";
import { attemptChips } from "@/lib/attemptChips";
import { makeRecordActor } from "@/lib/audio/recorder";
import {
  makePlayBlob,
  makePlayBoth,
  makePlayOriginalOnce,
} from "@/lib/player/listenActors";
import {
  makePlaySample,
  sampleWindow,
  type PlayableLesson,
} from "@/lib/player/playRange";
import {
  playerMachine,
  type RepeatCount,
  type UploadInput,
} from "@/lib/player/playerMachine";
import type { ShortcutToggle } from "@/lib/player/shortcuts";
import { useShortcuts } from "@/lib/player/useShortcuts";
import { bestBySegment } from "@/lib/progressView";
import {
  queryKeys,
  useAttemptResult,
  useAttempts,
  useLesson,
  useLessonProgress,
  useSettings,
  useSystemStatus,
} from "@/lib/queries";
import {
  nextViewedAttempt,
  resolveViewedResult,
  yoursAvailable,
} from "@/lib/viewedAttempt";

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

const UPLOAD_ERROR_TOAST_ID = "upload-error";
const UPLOAD_ERROR_TEXT =
  "Không xử lý được bản ghi. Bản ghi của bạn vẫn còn, bấm Thử lại để gửi lại.";

/** Trạng thái cấp trên cùng; scoring/reviewing/noVoice/error có trạng thái con nên `value` là object. */
function topLevelState(value: string | Record<string, unknown>): string {
  return typeof value === "string" ? value : (Object.keys(value)[0] ?? "");
}

interface PracticeRoomProps {
  lessonId: string;
}

export function PracticeRoom({ lessonId }: PracticeRoomProps) {
  const lesson = useLesson(lessonId);
  const progress = useLessonProgress(lessonId);
  const settings = useSettings();

  if (lesson.isError) {
    return (
      <RoomMessage
        title="Không tải được bài này."
        detail={lesson.error.message}
        onRetry={() => void lesson.refetch()}
      />
    );
  }
  if (lesson.isPending || progress.isPending || settings.isPending) {
    return <RoomSkeleton />;
  }
  // S1 chỉ liên kết tới bài `ready`; mở thẳng URL của bài chưa xong thì báo thay vì dựng máy trạng thái rỗng.
  if (lesson.data.status !== "ready" || lesson.data.segments.length === 0) {
    return (
      <RoomMessage
        title="Bài này chưa sẵn sàng để tập."
        detail="Quay lại Thư viện và mở lại khi bài đã tạo xong."
        onRetry={() => void lesson.refetch()}
      />
    );
  }

  return (
    <LoadedRoom
      lesson={lesson.data}
      progress={progress.data}
      settings={settings.data}
    />
  );
}

/** Lỗi tải bài (UI-SPEC E8 error): thông báo tại chỗ + `Tải lại` + liên kết về `Thư viện`. */
function RoomMessage({
  title,
  detail,
  onRetry,
}: {
  title: string;
  detail: string;
  onRetry: () => void;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center border-b border-border px-6 py-2.5">
        <BackToLibraryLink />
      </header>
      <main className="mx-auto flex w-full max-w-[720px] flex-col p-8">
        <Alert variant="error">
          <div className="flex flex-col gap-1">
            <AlertTitle>{title}</AlertTitle>
            <AlertDescription>{detail}</AlertDescription>
          </div>
          <AlertAction>
            <Button variant="outline" onClick={onRetry}>
              Tải lại
            </Button>
          </AlertAction>
        </Alert>
      </main>
    </div>
  );
}

/** Khung xương khi bài đang tải: hàng transcript và câu đang tập (UI-SPEC E8 loading). */
function RoomSkeleton() {
  return (
    <div aria-busy="true" className="flex h-screen flex-col">
      <header className="flex items-center gap-4 border-b border-border px-6 py-2.5">
        <BackToLibraryLink />
        <Skeleton className="h-4 w-48" />
      </header>
      <div className="flex min-h-0 flex-1 flex-wrap items-stretch overflow-y-auto min-[1160px]:flex-nowrap min-[1160px]:overflow-hidden">
        <aside
          aria-label="Video và transcript"
          className="flex min-w-[520px] flex-[0_1_600px] flex-col border-r border-border bg-[color:var(--slate-2)] min-[1160px]:min-h-0"
        >
          <div className="aspect-video w-full shrink-0 bg-video" />
          <TranscriptListSkeleton />
        </aside>
        <main className="flex min-w-0 flex-[999_1_560px] flex-col gap-4 px-12 pb-10 pt-9">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-[46px] w-full" />
          <Skeleton className="h-[46px] w-2/3" />
        </main>
      </div>
    </div>
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

  const lessonIdRef = useRef(lesson.id);
  useEffect(() => {
    lessonIdRef.current = lesson.id;
  }, [lesson.id]);

  // Machine tạo một lần: các actor đọc video/bài qua ref nên luôn thấy dữ liệu mới nhất.
  // Tải lên mặc định saveForEval=false; `Lưu clip cho eval` gửi lại riêng (REC-04, D-09).
  // `signal` huỷ yêu cầu khi rời trạng thái scoring (chuyển câu không thể xảy ra ở đó, nhưng unmount thì có).
  const [machine] = useState(() =>
    playerMachine.provide({
      actors: {
        playSample: makePlaySample(
          () => videoRef.current,
          () => lessonRef.current,
        ),
        playBlob: makePlayBlob(),
        playBoth: makePlayBoth(
          makePlayOriginalOnce(
            () => videoRef.current,
            () => lessonRef.current,
          ),
        ),
        record: makeRecordActor(),
        uploadAttempt: fromPromise<ScoreResult, UploadInput>(
          ({ input, signal }) =>
            uploadAttempt(lessonIdRef.current, input.segmentIndex, input.blob, {
              saveForEval: false,
              signal,
            }),
        ),
      },
    }),
  );

  const defaults = sessionDefaults(settings ?? DEFAULT_SETTINGS);
  const actorRef = useActorRef(machine, {
    input: {
      segmentCount: lesson.segments.length,
      startIndex: Math.min(
        progress?.firstUnpracticedIndex ?? 0,
        lesson.segments.length - 1,
      ),
      segmentDurationsMs: segmentDurationsMs(lesson),
      repeat: defaults.repeat,
      rate: defaults.rate,
      recordFactor: defaults.recordFactor,
    },
  });
  const snapshot = useSelector(actorRef, (state) => state);

  // Độ dài câu đổi (Mất chữ cuối?, kể cả sau khi tải lại bài): báo machine để đếm ngược ghi âm dùng độ dài mới.
  const durationsKey = segmentDurationsMs(lesson).join(",");
  const sentDurationsKey = useRef(durationsKey);
  useEffect(() => {
    if (sentDurationsKey.current === durationsKey) return;
    sentDurationsKey.current = durationsKey;
    actorRef.send({
      type: "SEGMENTS_UPDATED",
      segmentDurationsMs: segmentDurationsMs(lesson),
    });
  }, [durationsKey, lesson, actorRef]);
  const [videoReady, setVideoReady] = useState(false);
  // Lượt đã lưu clip cho eval trong phiên này, khoá `câu:lượt` (REC-04).
  const [savedClips, setSavedClips] = useState<ReadonlySet<string>>(new Set());
  // `So sánh ngữ điệu` mở/đóng: giữ khi chuyển câu trong phiên, không lưu (P3-G2).
  const [chartOpen, setChartOpen] = useState(false);

  const practiced = useMemo(
    () =>
      new Set(
        (progress?.segments ?? [])
          .filter((item) => item.voicedAttempts >= 1)
          .map((item) => item.segmentIndex),
      ),
    [progress],
  );
  // Điểm tốt nhất theo câu cho danh sách câu và thanh tiến độ (D-11).
  const best = useMemo(() => bestBySegment(progress), [progress]);

  const { context } = snapshot;
  const index = context.segmentIndex;
  const top = topLevelState(snapshot.value);

  // Kết quả chấm nhận trong phiên theo câu: machine chỉ giữ lượt mới nhất của mỗi câu, còn chip
  // phải giữ mọi lượt đã chấm (FBK-06). Danh sách server bổ sung khi tải lại trang.
  const [sessionResults, setSessionResults] = useState<
    Readonly<Record<number, readonly ScoreResult[]>>
  >({});
  const recording = context.recordings[index];
  // Lượt vừa chấm của câu (machine giữ đúng lượt mới nhất của mỗi câu).
  const latestResult =
    recording?.status === "scored" ? recording.result : undefined;
  const attempts = useAttempts(lesson.id, index);
  const sentenceSession = sessionResults[index];
  const sessionList = useMemo(() => {
    const kept = (sentenceSession ?? []).filter(
      (item) => item.attempt !== latestResult?.attempt,
    );
    return latestResult ? [...kept, latestResult] : [...kept];
  }, [sentenceSession, latestResult]);
  const chips = useMemo(
    () => attemptChips(attempts.data, sessionList),
    [attempts.data, sessionList],
  );

  // Lượt đang xem là state UI ngoài machine (UI-SPEC Interaction Contract). Mọi quy tắc nằm ở
  // `nextViewedAttempt`; ở đây chỉ báo sự kiện, ngay lúc render để không có khung hình lạc lượt.
  const [viewedAttempt, dispatchViewed] = useReducer(nextViewedAttempt, null);
  const [seen, setSeen] = useState({ index, chips });
  if (seen.index !== index) {
    setSeen({ index, chips });
    dispatchViewed({ type: "sentenceChanged", chips });
  } else if (seen.chips !== chips) {
    setSeen({ index, chips });
    dispatchViewed({ type: "chipsLoaded", chips });
  }
  // Lượt mới chấm (R) trở thành lượt đang xem và được giữ trong phiên để chip không mất lượt cũ (FBK-06).
  const [seenScoredKey, setSeenScoredKey] = useState<string | null>(null);
  const scoredKey = latestResult ? `${index}:${latestResult.attempt}` : null;
  if (latestResult && scoredKey !== seenScoredKey) {
    setSeenScoredKey(scoredKey);
    setSessionResults((prev) => ({
      ...prev,
      [index]: [
        ...(prev[index] ?? []).filter(
          (item) => item.attempt !== latestResult.attempt,
        ),
        latestResult,
      ],
    }));
    dispatchViewed({ type: "scored", attempt: latestResult.attempt });
  }

  // Kết quả đang xem: trong phiên thì dùng ngay; lượt cũ hơn thì tải bản đã lưu (D-11).
  const viewed = resolveViewedResult(viewedAttempt, sessionList, chips);
  const stored = useAttemptResult(
    lesson.id,
    index,
    viewed.kind === "stored" ? viewed.attempt : 0,
    viewed.kind === "stored",
  );

  // IPA (phím I) và bản dịch (phím T) là state UI, không đi vào machine.
  const [ipaOn, setIpaOn] = useState(false);
  const toggleIpa = useCallback(() => setIpaOn((on) => !on), []);
  const systemStatus = useSystemStatus();
  const translation = useTranslationTool({
    lessonId: lesson.id,
    segment: lesson.segments[index],
    hasKey: systemStatus.data?.hasKey ?? false,
  });
  const toggleTranslation = translation.toggle;
  const onToggle = useCallback(
    (toggle: ShortcutToggle) => {
      if (toggle.type === "TOGGLE_IPA") toggleIpa();
      else toggleTranslation();
    },
    [toggleIpa, toggleTranslation],
  );
  // Chỉ lượt đang xem có bản ghi trong phiên mới phát lại được M/B; các trạng thái khác giữ hành vi P1.
  const canPlayYours =
    top === "idle" || top === "reviewing"
      ? yoursAvailable(viewedAttempt, recording?.attempt)
      : true;
  useShortcuts(actorRef, { videoReady, onToggle, yoursEnabled: canPlayYours });

  // Lượt mới đã được server ghi nhận (reviewing hoặc noVoice sau scoring): cập nhật chấm "đã tập" và header.
  // Tải lên thất bại (scoring -> error): toast bền với `Thử lại`; rời error thì tắt toast (REC-03).
  const queryClient = useQueryClient();
  const previousTop = useRef(top);
  useEffect(() => {
    const was = previousTop.current;
    previousTop.current = top;
    if (was === "scoring" && (top === "reviewing" || top === "noVoice")) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.lessonProgress(lesson.id),
      });
    }
    if (was === "scoring" && top === "reviewing") {
      // Lượt vừa chấm: nạp sẵn cache chi tiết (bấm lại chip không cần tải) và làm mới danh sách
      // để chip khớp server.
      const machine = actorRef.getSnapshot().context;
      const result = machine.recordings[machine.segmentIndex]?.result;
      if (result) {
        const sentence = machine.segmentIndex;
        queryClient.setQueryData(
          queryKeys.attemptResult(lesson.id, sentence, result.attempt),
          result,
        );
        void queryClient.invalidateQueries({
          queryKey: queryKeys.attempts(lesson.id, sentence),
        });
      }
    }
    if (was === "scoring" && top === "error") {
      toast.error(UPLOAD_ERROR_TEXT, {
        id: UPLOAD_ERROR_TOAST_ID,
        duration: Infinity,
        closeButton: true,
        action: {
          label: "Thử lại",
          onClick: () => actorRef.send({ type: "RETRY_UPLOAD" }),
        },
      });
    } else if (was === "error" && top !== "error") {
      toast.dismiss(UPLOAD_ERROR_TOAST_ID);
    }
  }, [top, queryClient, lesson.id, actorRef]);
  // Rời S3 thì không để toast cũ nằm lại.
  useEffect(() => () => void toast.dismiss(UPLOAD_ERROR_TOAST_ID), []);

  // Tiến độ của lần phát hiện tại cho thanh trong SentenceStatePanel.
  const getPassProgress = useCallback(() => {
    const video = videoRef.current;
    const current = lesson.segments[index];
    if (!video || !current) return 0;
    const { startS, endS } = sampleWindow(
      current,
      lesson.padMs,
      lesson.durationSec,
    );
    return endS > startS ? (video.currentTime - startS) / (endS - startS) : 1;
  }, [lesson, index]);

  const segment = lesson.segments[index];
  if (!segment) return null;

  // Vùng kết quả chỉ hiện khi không có panel trạng thái nào chiếm chỗ (playing/recording/scoring/…).
  const resultVisible = top === "idle" || top === "reviewing";
  // Bản ghi trong phiên chỉ phát lại được khi chính là lượt đang xem (D-11).
  const viewedBlob =
    viewedAttempt !== null && recording?.attempt === viewedAttempt
      ? recording.blob
      : null;
  // Kết quả sẵn sàng để vẽ: lượt trong phiên, hoặc bản đã lưu khi tải xong.
  const viewedResult =
    viewed.kind === "session"
      ? viewed.result
      : viewed.kind === "stored"
        ? stored.data
        : undefined;
  const viewedOrdinal = viewed.kind === "none" ? 0 : viewed.ordinal;
  const storedFailed = viewed.kind === "stored" && stored.isError;
  // Câu thường chỉ hiện khi chưa có kết quả nào để xem; lỗi tải lượt cũ thì giữ câu cùng thông báo.
  const showPlainSentence = viewed.kind === "none" || storedFailed;

  const listening = top === "playing" || top === "previewing";

  return (
    <div className="flex h-screen flex-col">
      <PracticeHeader
        title={lesson.title}
        total={lesson.segments.length}
        currentIndex={index}
        practiced={practiced}
        best={best}
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
            best={best}
            onSelect={(next) => actorRef.send({ type: "GOTO", index: next })}
            lessonId={lesson.id}
            translation={translation}
            canEdit={
              top === "idle" ||
              top === "reviewing" ||
              top === "noVoice" ||
              top === "error"
            }
          />
        </aside>
        <main className="flex min-w-0 flex-[999_1_560px] flex-col gap-8 px-12 pb-10 pt-9 min-[1160px]:overflow-y-auto">
          <AttemptStrip
            lessonId={lesson.id}
            segmentIndex={segment.index}
            sentenceNumber={index + 1}
            chips={chips}
            viewedAttempt={viewedAttempt}
            onSelectAttempt={(attempt) =>
              dispatchViewed({ type: "selected", attempt })
            }
            ipaOn={ipaOn}
            onToggleIpa={toggleIpa}
          />
          {listening ? (
            <SentenceStatePanel
              variant="playing"
              sentence={segment.text}
              repeat={top === "playing" ? context.repeat : 1}
              rep={context.rep}
              autoRecord={top === "playing"}
              getPassProgress={getPassProgress}
            />
          ) : top === "recording" ? (
            <SentenceStatePanel
              variant="recording"
              sentence={segment.text}
              bars={context.level.bars}
            />
          ) : top === "scoring" ? (
            <SentenceStatePanel variant="scoring" sentence={segment.text} />
          ) : top === "noVoice" ? (
            <SentenceStatePanel
              variant="noVoice"
              sentence={segment.text}
              onRecord={() => actorRef.send({ type: "RECORD" })}
            />
          ) : top === "error" && context.lastError === "mic" ? (
            <SentenceStatePanel
              variant="micError"
              sentence={segment.text}
              onRecord={() => actorRef.send({ type: "RECORD" })}
            />
          ) : top === "error" ? (
            <SentenceStatePanel
              variant="uploadError"
              sentence={segment.text}
              onRetry={() => actorRef.send({ type: "RETRY_UPLOAD" })}
              onRecord={() => actorRef.send({ type: "RECORD" })}
            />
          ) : !showPlainSentence ? null : (
            <p className="m-0 text-[38px] font-semibold leading-[1.2] tracking-[-0.015em]">
              {segment.text}
            </p>
          )}
          {ipaOn && top === "idle" && showPlainSentence ? (
            <SpokenIpa words={segment.words} />
          ) : null}
          {resultVisible && storedFailed ? (
            <Alert>
              <AlertDescription>
                Không tải được kết quả của lượt này.
              </AlertDescription>
              <AlertAction>
                <Button variant="outline" onClick={() => void stored.refetch()}>
                  Thử lại
                </Button>
              </AlertAction>
            </Alert>
          ) : resultVisible && viewed.kind === "stored" && !viewedResult ? (
            <div aria-busy="true">
              <MetricSkeleton />
            </div>
          ) : resultVisible && viewedAttempt !== null && viewedResult ? (
            <ResultPanel
              key={`${index}:${viewedAttempt}`}
              lessonId={lesson.id}
              segmentIndex={index}
              segment={segment}
              result={viewedResult}
              attemptLabel={viewedOrdinal}
              ipaOn={ipaOn}
              blob={viewedBlob}
              chartOpen={chartOpen}
              onChartOpenChange={setChartOpen}
              saved={savedClips.has(`${index}:${viewedAttempt}`)}
              onSaved={() => {
                const key = `${index}:${viewedAttempt}`;
                setSavedClips((prev) => new Set(prev).add(key));
              }}
            />
          ) : null}
        </main>
      </div>
      <ResultActionBar
        stateValue={snapshot.value}
        segmentIndex={index}
        segmentCount={context.segmentCount}
        hasRecording={recording !== undefined}
        yoursAvailable={canPlayYours}
        videoReady={videoReady}
        send={actorRef.send}
      />
    </div>
  );
}
