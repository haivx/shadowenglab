import { describe, expect, it, vi } from "vitest";
import {
  playBlobOnce,
  type AudioLike,
  type BlobPlaybackDeps,
} from "./listenActors";

function fakeDeps(options: { playRejects?: boolean } = {}) {
  const revoked: string[] = [];
  let audio: FakeAudio | undefined;
  class FakeAudio implements AudioLike {
    onended: (() => void) | null = null;
    onerror: (() => void) | null = null;
    paused = 0;
    play() {
      return options.playRejects
        ? Promise.reject(new Error("blocked"))
        : Promise.resolve();
    }
    pause() {
      this.paused += 1;
    }
  }
  const deps: BlobPlaybackDeps = {
    createUrl: () => "blob:fake-1",
    revokeUrl: (url) => revoked.push(url),
    createAudio: () => {
      audio = new FakeAudio();
      return audio;
    },
  };
  return { deps, revoked, getAudio: () => audio };
}

describe("playBlobOnce", () => {
  it("resolve khi phát xong và thu hồi object URL", async () => {
    const { deps, revoked, getAudio } = fakeDeps();
    const done = playBlobOnce(
      new Blob(["x"]),
      new AbortController().signal,
      deps,
    );
    getAudio()?.onended?.();
    await expect(done).resolves.toBeUndefined();
    expect(revoked).toEqual(["blob:fake-1"]);
  });

  it("huỷ giữa chừng thì pause, reject AbortError và thu hồi URL", async () => {
    const { deps, revoked, getAudio } = fakeDeps();
    const controller = new AbortController();
    const done = playBlobOnce(new Blob(["x"]), controller.signal, deps);
    controller.abort();
    await expect(done).rejects.toMatchObject({ name: "AbortError" });
    expect(getAudio()?.paused).toBe(1);
    expect(revoked).toEqual(["blob:fake-1"]);
  });

  it("signal đã huỷ từ trước thì không tạo URL", async () => {
    const createUrl = vi.fn(() => "blob:never");
    const controller = new AbortController();
    controller.abort();
    await expect(
      playBlobOnce(new Blob(["x"]), controller.signal, {
        createUrl,
        revokeUrl: () => undefined,
        createAudio: () => {
          throw new Error("không được tạo audio");
        },
      }),
    ).rejects.toMatchObject({ name: "AbortError" });
    expect(createUrl).not.toHaveBeenCalled();
  });

  it("play() bị từ chối thì reject và vẫn thu hồi URL", async () => {
    const { deps, revoked } = fakeDeps({ playRejects: true });
    await expect(
      playBlobOnce(new Blob(["x"]), new AbortController().signal, deps),
    ).rejects.toThrow("blocked");
    expect(revoked).toEqual(["blob:fake-1"]);
  });
});
