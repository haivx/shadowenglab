import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError, listLessons } from "./api";

const FIXTURE_DIR = join(
  import.meta.dirname,
  "..",
  "..",
  "..",
  "packages",
  "contracts",
  "fixtures",
);

interface FixtureCase {
  name: string;
  data: unknown;
}

function loadFixture(file: string): FixtureCase[] {
  return JSON.parse(readFileSync(join(FIXTURE_DIR, file), "utf8"));
}

function fixtureData(file: string, name: string): unknown {
  const found = loadFixture(file).find((c) => c.name === name);
  if (!found) throw new Error(`fixture ${file}#${name} not found`);
  return found.data;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function catchError(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise;
  } catch (error) {
    return error;
  }
  throw new Error("expected the promise to reject");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("listLessons", () => {
  it("parses the LessonListItem fixture array", async () => {
    const items = loadFixture("LessonListItem.json").map((c) => c.data);
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(items));
    vi.stubGlobal("fetch", fetchMock);

    const result = await listLessons();

    expect(result).toHaveLength(items.length);
    expect(result[0]?.lesson.id).toBe("01JABCDEFGHJKMNPQRSTVWXYZ0");
    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/lessons$/);
  });

  it("throws ApiRequestError carrying lessonId on a 409 duplicate_lesson body", async () => {
    const body = fixtureData("ApiError.json", "duplicate-lesson");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body, 409)));

    const error = await catchError(listLessons());

    expect(error).toBeInstanceOf(ApiRequestError);
    const failure = error as ApiRequestError;
    expect(failure.status).toBe(409);
    expect(failure.error.code).toBe("duplicate_lesson");
    expect(failure.error.lessonId).toBe("01JABCDEFGHJKMNPQRSTVWXYZ0");
  });

  it("falls back to internal_error on a 500 with a non-JSON body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<html>boom</html>", {
          status: 500,
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );

    const error = await catchError(listLessons());

    expect(error).toBeInstanceOf(ApiRequestError);
    const failure = error as ApiRequestError;
    expect(failure.status).toBe(500);
    expect(failure.error.code).toBe("internal_error");
    expect(failure.error.message).toBe("Backend trả lỗi không đọc được.");
  });

  it("maps a rejected fetch to status 0 with the Vietnamese unreachable message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );

    const error = await catchError(listLessons());

    expect(error).toBeInstanceOf(ApiRequestError);
    const failure = error as ApiRequestError;
    expect(failure.status).toBe(0);
    expect(failure.error.code).toBe("internal_error");
    expect(failure.error.message).toBe(
      "Không kết nối được backend. Chạy make dev rồi bấm Tải lại.",
    );
  });

  it("throws when a 200 body violates the schema", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse([{ lesson: { id: 1 } }])),
    );

    await expect(listLessons()).rejects.toThrow();
  });
});
