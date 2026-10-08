"use client";

import type { AppSettings, ModelState } from "@shadowenglab/contracts";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiRequestError, putSettings } from "@/lib/api";
import { queryKeys, useSettings, useSystemStatus } from "@/lib/queries";
import {
  SETTINGS_SECTION_CLASS,
  dataDirNeedsRestart,
} from "@/lib/settingsForm";
import { cn } from "@/lib/utils";

const MODEL_ROWS = [
  { key: "demucs", label: "Demucs · tách giọng" },
  { key: "whisper", label: "mlx-whisper · phiên âm" },
  { key: "wav2vec2", label: "wav2vec2-espeak · chấm âm" },
] as const;

const STATUS_COPY: Record<ModelState, { text: string; className: string }> = {
  ready: { text: "Sẵn sàng", className: "text-success-text" },
  loading: { text: "Đang nạp…", className: "text-muted-foreground" },
  missing: {
    text: "Chưa có · chạy make setup",
    className: "text-destructive-text",
  },
};

const BAD_DIR = "Thư mục không tồn tại hoặc không ghi được.";
const SAVE_FAILED = "Không lưu được. Thử lại.";
const BACKEND_DOWN =
  "Không kết nối được backend. Chạy make dev rồi bấm Tải lại.";

interface DataDirRowProps {
  /** Cài đặt đã tải; `null` = không tải được, chỉ hiện thư mục đang dùng, không sửa được. */
  settings: AppSettings | null;
  activeDataDir: string;
}

/** Hàng `Thư mục dữ liệu` (D-12, SET-04): sửa được, đổi thì chỉ có hiệu lực sau khi khởi động lại. */
function DataDirRow({ settings, activeDataDir }: DataDirRowProps) {
  const inputId = useId();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState(settings?.dataDir ?? activeDataDir);

  const change = useMutation({
    mutationFn: (dataDir: string) => {
      const current =
        queryClient.getQueryData<AppSettings>(queryKeys.settings) ?? settings;
      if (!current) throw new Error("settings_unavailable");
      return putSettings({ ...current, dataDir, accent: "US" });
    },
    onSuccess: (next) => {
      queryClient.setQueryData(queryKeys.settings, next);
      // Server có thể chuẩn hoá đường dẫn (~, dấu gạch cuối); hiện đúng giá trị đã lưu.
      setDraft(next.dataDir);
    },
  });

  const saved = settings?.dataDir ?? activeDataDir;
  const trimmed = draft.trim();
  const canSubmit =
    settings !== null &&
    !change.isPending &&
    trimmed !== "" &&
    trimmed !== saved;

  let message: { text: string; tone: "success" | "destructive" } | null = null;
  if (change.isError) {
    const invalid =
      change.error instanceof ApiRequestError &&
      change.error.error.code === "invalid_settings";
    message = { text: invalid ? BAD_DIR : SAVE_FAILED, tone: "destructive" };
  } else if (change.isSuccess) {
    message = {
      text: dataDirNeedsRestart(change.data.dataDir, activeDataDir)
        ? `Khởi động lại make dev để áp dụng; dữ liệu cũ vẫn ở ${activeDataDir}.`
        : "Đã lưu",
      tone: "success",
    };
  }

  return (
    <form
      className="flex flex-col gap-2 pt-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSubmit) change.mutate(trimmed);
      }}
    >
      <Label htmlFor={inputId}>Thư mục dữ liệu</Label>
      <div className="flex flex-wrap gap-2">
        <Input
          id={inputId}
          value={draft}
          title={draft}
          spellCheck={false}
          disabled={settings === null}
          aria-invalid={change.isError && message?.text === BAD_DIR}
          onChange={(event) => {
            setDraft(event.target.value);
            if (!change.isPending) change.reset();
          }}
          className="flex-[1_1_280px] truncate font-mono text-[13px]"
        />
        <Button type="submit" variant="outline" disabled={!canSubmit}>
          Đổi thư mục
        </Button>
      </div>
      <span
        role="status"
        className={cn(
          "min-h-[1.25rem] text-[13px] font-semibold",
          message?.tone === "success" && "text-success-text",
          message?.tone === "destructive" && "text-destructive-text",
        )}
      >
        {message?.text}
      </span>
    </form>
  );
}

/** Mục `Model và dữ liệu` của S8: trạng thái từng model (D-13) và thư mục dữ liệu. */
export function ModelStatusList() {
  const headingId = useId();
  const status = useSystemStatus();
  const settings = useSettings();

  let body;
  if (status.data) {
    const { models, activeDataDir } = status.data;
    body = (
      <>
        <ul className="flex list-none flex-col text-sm">
          {MODEL_ROWS.map(({ key, label }) => {
            const copy = STATUS_COPY[models[key]];
            return (
              <li
                key={key}
                className="flex flex-col gap-1.5 border-b border-muted py-2.5"
              >
                <span className="flex justify-between gap-3">
                  <span>{label}</span>
                  <span className={cn("font-semibold", copy.className)}>
                    {copy.text}
                  </span>
                </span>
                {models[key] === "loading" ? (
                  <Progress indeterminate aria-label={`${label}: đang nạp`} />
                ) : null}
              </li>
            );
          })}
        </ul>
        {settings.isPending ? (
          <Skeleton className="h-[88px] w-full" />
        ) : (
          <DataDirRow
            // Mount lại khi bản cài đặt đầu tiên về hoặc khi chuyển giữa tải được / không tải được.
            key={settings.data ? "loaded" : "unavailable"}
            settings={settings.data ?? null}
            activeDataDir={activeDataDir}
          />
        )}
      </>
    );
  } else if (status.isError) {
    body = (
      <div
        role="status"
        className="flex flex-wrap items-center gap-3 text-sm font-semibold text-destructive-text"
      >
        <span>{BACKEND_DOWN}</span>
        <Button variant="outline" onClick={() => void status.refetch()}>
          Tải lại
        </Button>
      </div>
    );
  } else {
    body = (
      <div
        className="flex flex-col gap-3"
        aria-busy="true"
        aria-label="Đang tải trạng thái model"
      >
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-full" />
      </div>
    );
  }

  return (
    <section className={SETTINGS_SECTION_CLASS} aria-labelledby={headingId}>
      <h2 id={headingId} className="text-lg font-bold leading-tight">
        Model và dữ liệu
      </h2>
      {body}
    </section>
  );
}
