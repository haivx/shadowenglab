import {
  ApiError,
  AppSettings,
  AttemptAck,
  CreateLessonRequest,
  Lesson,
  LessonListItem,
  LessonProgress,
  OpenAiKeyCheckRequest,
  OpenAiKeyCheckResult,
  ScoreResult,
  Segment,
  SystemStatus,
  UpdateSegmentTextRequest,
  VideoPreview,
} from "@shadowenglab/contracts";

/**
 * Client API duy nhất của web (CLAUDE.md: Zod ở mọi ranh giới I/O).
 * Mọi phản hồi 2xx đi qua `Schema.parse`; lỗi đi qua phong bì `ApiError`.
 */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const NETWORK_ERROR_MESSAGE =
  "Không kết nối được backend. Chạy make dev rồi bấm Tải lại.";
const UNREADABLE_ERROR_MESSAGE = "Backend trả lỗi không đọc được.";

/** Lỗi gọi API. `status` = 0 khi không kết nối được backend. */
export class ApiRequestError extends Error {
  readonly status: number;
  readonly error: ApiError;

  constructor(status: number, error: ApiError) {
    super(error.message);
    this.name = "ApiRequestError";
    this.status = status;
    this.error = error;
  }
}

/** Chỉ cần `parse`: tránh phụ thuộc trực tiếp vào zod ở apps/web. */
interface Parser<T> {
  parse(data: unknown): T;
}

function enc(value: string | number): string {
  return encodeURIComponent(String(value));
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

async function send(path: string, init: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch (cause) {
    // Huỷ có chủ đích (AbortController) không phải lỗi backend.
    if (cause instanceof DOMException && cause.name === "AbortError") {
      throw cause;
    }
    throw new ApiRequestError(0, {
      code: "internal_error",
      message: NETWORK_ERROR_MESSAGE,
    });
  }
  if (!response.ok) {
    const parsed = ApiError.safeParse(await readJson(response));
    throw new ApiRequestError(
      response.status,
      parsed.success
        ? parsed.data
        : { code: "internal_error", message: UNREADABLE_ERROR_MESSAGE },
    );
  }
  return response;
}

async function request<T>(
  path: string,
  init: RequestInit,
  schema: Parser<T>,
): Promise<T> {
  const response = await send(path, init);
  return schema.parse(await readJson(response));
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

const lessonPath = (id: string) => `/lessons/${enc(id)}`;
const segmentPath = (id: string, index: number) =>
  `${lessonPath(id)}/segments/${enc(index)}`;

export function getSystemStatus(): Promise<SystemStatus> {
  return request("/system/status", { method: "GET" }, SystemStatus);
}

export function getSettings(): Promise<AppSettings> {
  return request("/settings", { method: "GET" }, AppSettings);
}

export function putSettings(settings: AppSettings): Promise<AppSettings> {
  return request(
    "/settings",
    jsonInit("PUT", AppSettings.parse(settings)),
    AppSettings,
  );
}

/** `apiKey` vắng mặt = kiểm tra key đã lưu. */
export function checkOpenAiKey(apiKey?: string): Promise<OpenAiKeyCheckResult> {
  const body: OpenAiKeyCheckRequest = OpenAiKeyCheckRequest.parse(
    apiKey === undefined ? {} : { apiKey },
  );
  return request(
    "/settings/openai-key/check",
    jsonInit("POST", body),
    OpenAiKeyCheckResult,
  );
}

export function previewVideo(url: string): Promise<VideoPreview> {
  const query = new URLSearchParams({ url }).toString();
  return request(`/videos/preview?${query}`, { method: "GET" }, VideoPreview);
}

export function createLesson(input: CreateLessonRequest): Promise<Lesson> {
  return request(
    "/lessons",
    jsonInit("POST", CreateLessonRequest.parse(input)),
    Lesson,
  );
}

export function listLessons(): Promise<LessonListItem[]> {
  return request("/lessons", { method: "GET" }, LessonListItem.array());
}

export function getLesson(id: string): Promise<Lesson> {
  return request(lessonPath(id), { method: "GET" }, Lesson);
}

export function retryLesson(id: string): Promise<Lesson> {
  return request(`${lessonPath(id)}/retry`, { method: "POST" }, Lesson);
}

export function getLessonProgress(id: string): Promise<LessonProgress> {
  return request(
    `${lessonPath(id)}/progress`,
    { method: "GET" },
    LessonProgress,
  );
}

/** Chỉ dựng URL cho thẻ video (hỗ trợ Range phía server). */
export function lessonVideoUrl(id: string): string {
  return `${API_BASE}${lessonPath(id)}/video`;
}

/** 204 không có body. */
export async function reloadLessonVideo(id: string): Promise<void> {
  await send(`${lessonPath(id)}/video/reload`, { method: "POST" });
}

export function updateSegmentText(
  id: string,
  index: number,
  text: string,
): Promise<Segment> {
  const body = UpdateSegmentTextRequest.parse({ text });
  return request(segmentPath(id, index), jsonInit("PATCH", body), Segment);
}

/** Server tự cộng 300 ms vào `endExtraMs` (quyết định E). */
export function extendSegmentEnd(id: string, index: number): Promise<Segment> {
  return request(
    `${segmentPath(id, index)}/extend-end`,
    { method: "POST" },
    Segment,
  );
}

export function translateSegment(id: string, index: number): Promise<Segment> {
  return request(
    `${segmentPath(id, index)}/translate`,
    { method: "POST" },
    Segment,
  );
}

export interface UploadAttemptOptions {
  saveForEval: boolean;
  signal?: AbortSignal;
}

/**
 * Tải bản ghi lên và nhận kết quả chấm trong cùng request (A2, D-09). Phản hồi 2xx đi qua
 * `ScoreResult.parse`; 422 `no_speech` thành `ApiRequestError` để machine rẽ sang noVoice.
 */
export function uploadAttempt(
  lessonId: string,
  index: number,
  blob: Blob,
  options: UploadAttemptOptions,
): Promise<ScoreResult> {
  const form = new FormData();
  form.append("audio", blob, "attempt");
  form.append("saveForEval", options.saveForEval ? "true" : "false");
  return request(
    `${segmentPath(lessonId, index)}/attempts`,
    { method: "POST", body: form, signal: options.signal },
    ScoreResult,
  );
}

/** Gửi lại blob của một lượt đã có để lưu cho eval; không tạo lượt mới. */
export function saveEvalClip(
  lessonId: string,
  index: number,
  attempt: number,
  blob: Blob,
): Promise<AttemptAck> {
  const form = new FormData();
  form.append("audio", blob, "attempt");
  return request(
    `${segmentPath(lessonId, index)}/attempts/${enc(attempt)}/eval-clip`,
    { method: "PUT", body: form },
    AttemptAck,
  );
}
