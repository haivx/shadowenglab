import * as z from "zod";

/**
 * Cài đặt người dùng (D-10). Không có giá trị mặc định trong contract:
 * server điền mặc định (1, 1, 1.5, thư mục dữ liệu hiện tại, "US").
 */
export const AppSettings = z
  .object({
    playbackRate: z.number().min(0.5).max(1),
    repeat: z.union([z.literal(1), z.literal(2), z.literal(3)]),
    recordFactor: z.number().min(1).max(2),
    dataDir: z.string(),
    accent: z.literal("US"),
  })
  .meta({ id: "AppSettings" });

/** Trạng thái một model nặng (D-13). Không có meta id: inline thành Literal. */
export const ModelState = z.enum(["missing", "loading", "ready"]);

export const ModelStatuses = z
  .object({
    demucs: ModelState,
    whisper: ModelState,
    wav2vec2: ModelState,
  })
  .meta({ id: "ModelStatuses" });

/** Trạng thái hệ thống (D-13). Trạng thái mic nằm phía client. */
export const SystemStatus = z
  .object({
    models: ModelStatuses,
    hasKey: z.boolean(),
    maskedKey: z.string().optional(),
    activeDataDir: z.string(),
  })
  .meta({ id: "SystemStatus" });

/** `apiKey` vắng mặt = kiểm tra key đã lưu (D-11, SET-03). */
export const OpenAiKeyCheckRequest = z
  .object({ apiKey: z.string().optional() })
  .meta({ id: "OpenAiKeyCheckRequest" });

/** `valid: null` = không kiểm tra được (cố ý nullable, khác với optional). */
export const OpenAiKeyCheckResult = z
  .object({
    valid: z.boolean().nullable(),
    saved: z.boolean(),
    maskedKey: z.string().optional(),
    reason: z.enum(["invalid", "network", "no_key"]).optional(),
  })
  .meta({ id: "OpenAiKeyCheckResult" });

export type AppSettings = z.infer<typeof AppSettings>;
export type ModelState = z.infer<typeof ModelState>;
export type ModelStatuses = z.infer<typeof ModelStatuses>;
export type SystemStatus = z.infer<typeof SystemStatus>;
export type OpenAiKeyCheckRequest = z.infer<typeof OpenAiKeyCheckRequest>;
export type OpenAiKeyCheckResult = z.infer<typeof OpenAiKeyCheckResult>;
