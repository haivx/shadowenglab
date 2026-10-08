"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { LevelMeter } from "@/components/LevelMeter";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createLevelState, updateLevel } from "@/lib/audio/level";
import { useMicPermission } from "@/lib/audio/micPermission";
import {
  MIC_DEVICE_STORAGE_KEY,
  openMic,
  type MicHandle,
} from "@/lib/audio/recorder";
import { micPermissionLabel, SETTINGS_SECTION_CLASS } from "@/lib/settingsForm";
import { cn } from "@/lib/utils";

/** Thử micro nghe đúng 3 giây rồi đóng micro (T-02-48). */
const TEST_DURATION_MS = 3000;

const NO_DEVICE = "Không tìm thấy micro";
const OPEN_FAILED =
  "Không mở được micro. Cho phép micro cho localhost:3000 hoặc chọn micro khác.";

interface DeviceOption {
  id: string;
  label: string;
}

type TestState =
  | { phase: "idle" }
  | { phase: "listening"; bars: number }
  | { phase: "done"; heard: boolean }
  | { phase: "failed" };

function readSavedDeviceId(): string | null {
  try {
    return window.localStorage.getItem(MIC_DEVICE_STORAGE_KEY);
  } catch {
    return null;
  }
}

function saveDeviceId(deviceId: string): void {
  try {
    window.localStorage.setItem(MIC_DEVICE_STORAGE_KEY, deviceId);
  } catch {
    // Chế độ riêng tư chặn localStorage: lựa chọn chỉ có hiệu lực tới khi tải lại trang.
  }
}

async function listAudioInputs(): Promise<DeviceOption[]> {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices
      .filter((device) => device.kind === "audioinput" && device.deviceId)
      .map((device, index) => ({
        id: device.deviceId,
        // Nhãn chỉ có sau khi được cấp quyền micro.
        label: device.label || `Micro ${index + 1}`,
      }));
  } catch {
    return [];
  }
}

/**
 * Mục `Micro` của S8 (SET-01, G12, G18): chọn thiết bị (lưu localStorage, không nằm trong
 * AppSettings), `Thử micro` 3 giây với đồng hồ mức âm, và dòng quyền micro.
 */
export function MicSection() {
  const selectId = useId();
  const permission = useMicPermission();
  const [devices, setDevices] = useState<DeviceOption[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [test, setTest] = useState<TestState>({ phase: "idle" });
  const session = useRef<{ dispose: () => void } | null>(null);

  const refreshDevices = useCallback(async () => {
    const found = await listAudioInputs();
    setDevices(found);
    const saved = readSavedDeviceId();
    setDeviceId((current) => {
      const wanted = current || saved || "";
      return found.some((device) => device.id === wanted)
        ? wanted
        : (found[0]?.id ?? "");
    });
  }, []);

  useEffect(() => {
    void refreshDevices();
    const media = navigator.mediaDevices;
    if (!media?.addEventListener) return undefined;
    const onChange = () => void refreshDevices();
    media.addEventListener("devicechange", onChange);
    return () => media.removeEventListener("devicechange", onChange);
  }, [refreshDevices]);

  // Rời trang giữa lúc đang thử: trả micro ngay.
  useEffect(
    () => () => {
      session.current?.dispose();
    },
    [],
  );

  const onSelect = (next: string) => {
    setDeviceId(next);
    saveDeviceId(next);
  };

  const startTest = async () => {
    if (session.current) return;
    let disposed = false;
    let handle: MicHandle | undefined;
    let rafId: number | null = null;
    const stopTimer: { id?: ReturnType<typeof setTimeout> } = {};
    const dispose = () => {
      disposed = true;
      if (rafId !== null) cancelAnimationFrame(rafId);
      if (stopTimer.id !== undefined) clearTimeout(stopTimer.id);
      handle?.close();
      session.current = null;
    };
    session.current = { dispose };
    setTest({ phase: "listening", bars: 0 });

    try {
      handle = await openMic(deviceId || undefined);
    } catch {
      if (!disposed) {
        session.current = null;
        setTest({ phase: "failed" });
      }
      return;
    }
    if (disposed) {
      handle.close();
      return;
    }

    // Quyền vừa được cấp: nhãn thiết bị đã đọc được.
    void refreshDevices();

    const mic = handle;
    const buffer = new Float32Array(mic.analyser.fftSize);
    let level = createLevelState();
    let heard = false;
    let lastTime = performance.now();
    let lastBars = 0;
    const tick = () => {
      rafId = null;
      if (disposed) return;
      const now = performance.now();
      mic.analyser.getFloatTimeDomainData(buffer);
      level = updateLevel(level, buffer, Math.max(0, now - lastTime));
      lastTime = now;
      if (level.speech) heard = true;
      if (level.bars !== lastBars) {
        lastBars = level.bars;
        setTest({ phase: "listening", bars: level.bars });
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    stopTimer.id = setTimeout(() => {
      if (disposed) return;
      dispose();
      setTest({ phase: "done", heard });
    }, TEST_DURATION_MS);
  };

  const listening = test.phase === "listening";
  const noDevice = devices.length === 0;

  let resultText: string | null = null;
  let resultClass = "text-muted-foreground";
  if (test.phase === "listening") {
    resultText = "Đang nghe…";
  } else if (test.phase === "done") {
    resultText = test.heard ? "Nghe thấy tiếng" : "Không nghe thấy gì";
    resultClass = test.heard ? "text-success-text" : "text-destructive-text";
  } else if (test.phase === "failed") {
    resultText = OPEN_FAILED;
    resultClass = "text-destructive-text";
  }

  return (
    <section
      className={SETTINGS_SECTION_CLASS}
      aria-labelledby={`${selectId}-h`}
    >
      <h2 id={`${selectId}-h`} className="text-lg font-bold leading-tight">
        Micro
      </h2>
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-[1_1_280px] flex-col gap-1.5">
          <Label htmlFor={selectId}>Thiết bị</Label>
          <Select
            value={deviceId}
            onValueChange={onSelect}
            disabled={noDevice || listening}
          >
            <SelectTrigger id={selectId}>
              <SelectValue placeholder={NO_DEVICE} />
            </SelectTrigger>
            <SelectContent>
              {devices.map((device) => (
                <SelectItem key={device.id} value={device.id}>
                  {device.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button
          variant="outline"
          onClick={() => void startTest()}
          disabled={noDevice || listening}
        >
          Thử micro
        </Button>
      </div>
      {listening ? <LevelMeter bars={test.bars} /> : null}
      <div className="flex flex-col gap-1">
        <span
          role="status"
          className={cn(
            "min-h-[1.25rem] text-[13px] font-semibold",
            resultClass,
          )}
        >
          {resultText}
        </span>
        <span className="text-[13px] text-muted-foreground">
          Quyền micro: {micPermissionLabel(permission)}
        </span>
      </div>
    </section>
  );
}
