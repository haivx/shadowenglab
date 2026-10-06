import * as z from "zod";

// Primitives dùng chung. Cố ý KHÔNG có `.meta({ id })` để chúng được inline vào từng $defs.

/** Giây (float), tính từ đầu video gốc (D-01). */
export const Seconds = z.number().min(0);

/** Mili-giây nguyên (D-01). */
export const Milliseconds = z.number().int().min(0);

/** Điểm 0..1 (D-03). */
export const Score01 = z.number().min(0).max(1);

/** Xác suất 0..1. */
export const Probability = z.number().min(0).max(1);

/** Timestamp ISO-8601 dạng chuỗi thường (Pitfall 7: không dùng z.iso.datetime()). */
export const IsoTimestamp = z.string();
