"use client";

import type { AppSettings } from "@shadowenglab/contracts";
import { useQueryClient } from "@tanstack/react-query";
import { useId, useReducer, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { putSettings } from "@/lib/api";
import { queryKeys, useSettings } from "@/lib/queries";
import {
  DEFAULT_PLAYBACK_RATE,
  DEFAULT_RECORD_FACTOR,
  DEFAULT_REPEAT,
  RATE_OPTIONS,
  RECORD_FACTOR_OPTIONS,
  REPEAT_OPTIONS,
  SETTINGS_SECTION_CLASS,
  initialField,
  settingsReducer,
  snapToOption,
  type Option,
} from "@/lib/settingsForm";

const SAVED = "Đã lưu";
const SAVE_FAILED = "Không lưu được. Thử lại.";
const LOAD_FAILED = "Không tải được cài đặt. Đang dùng giá trị mặc định.";

interface AutoSaveSelectProps<T extends number> {
  label: string;
  options: readonly Option<T>[];
  /** Giá trị backend đã xác nhận lúc mở trang. */
  initial: T;
  /** Khoá mọi ô trong lúc một ô đang lưu, hoặc khi không có cài đặt để ghi đè. */
  disabled: boolean;
  /** Ném lỗi khi backend không lưu được. */
  onSave: (value: T) => Promise<void>;
}

/**
 * Select tự lưu (SET-04, D-10). Đổi là hiện ngay và PUT; thất bại thì hoàn tác về giá trị
 * đã lưu, báo `Không lưu được. Thử lại.` kèm nút `Thử lại` gửi lại giá trị vừa chọn.
 * Không bao giờ hiện một giá trị chưa lưu như đã lưu (E13).
 */
function AutoSaveSelect<T extends number>({
  label,
  options,
  initial,
  disabled,
  onSave,
}: AutoSaveSelectProps<T>) {
  const id = useId();
  const [state, dispatch] = useReducer(
    settingsReducer<T>,
    initial,
    initialField<T>,
  );

  const save = (value: T) => {
    onSave(value).then(
      () => dispatch({ type: "success", value }),
      () => dispatch({ type: "failure", value }),
    );
  };

  const onValueChange = (raw: string) => {
    const option = options.find((candidate) => String(candidate.value) === raw);
    if (!option || option.value === state.display) return;
    dispatch({ type: "change", value: option.value });
    save(option.value);
  };

  const onRetry = () => {
    if (state.pending === undefined) return;
    dispatch({ type: "retry" });
    save(state.pending);
  };

  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Select
        value={String(state.display)}
        onValueChange={onValueChange}
        disabled={disabled}
      >
        <SelectTrigger id={id} aria-busy={state.status === "saving"}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={String(option.value)}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <div role="status" className="flex flex-col items-start gap-1">
        {state.status === "saved" ? (
          <span className="text-[13px] font-semibold text-success-text">
            {SAVED}
          </span>
        ) : null}
        {state.status === "error" ? (
          <>
            <span className="text-[13px] font-semibold text-destructive-text">
              {SAVE_FAILED}
            </span>
            <Button variant="outline" onClick={onRetry} disabled={disabled}>
              Thử lại
            </Button>
          </>
        ) : null}
      </div>
    </div>
  );
}

function LockedAccentRow() {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-[color:var(--slate-2)] px-4 py-3.5">
      <span className="flex flex-col gap-0.5">
        <span className="text-sm font-semibold">
          Giọng mục tiêu: Anh Mỹ (US)
        </span>
        <span className="text-[13px] text-muted-foreground">
          Giọng Anh (UK) sẽ có ở bản sau.
        </span>
      </span>
      <Badge>Cố định</Badge>
    </div>
  );
}

const GRID_CLASS = "grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-4";

/** `settings === null`: đang dùng mặc định vì không tải được, không thể ghi đè nên khoá các ô. */
function PracticeForm({ settings }: { settings: AppSettings | null }) {
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);

  const persist = async (patch: Partial<AppSettings>) => {
    // Luôn dựng từ bản đã lưu mới nhất (mục `Model và dữ liệu` cũng ghi cùng tệp), tránh đè
    // ngược giá trị khác bằng bản cũ.
    const base = queryClient.getQueryData<AppSettings>(queryKeys.settings);
    const current = base ?? settings;
    if (!current) throw new Error("settings_unavailable");
    setBusy(true);
    try {
      const next = await putSettings({ ...current, ...patch, accent: "US" });
      queryClient.setQueryData(queryKeys.settings, next);
    } finally {
      setBusy(false);
    }
  };

  const disabled = busy || settings === null;

  return (
    <>
      <div className={GRID_CLASS}>
        <AutoSaveSelect
          label="Tốc độ mặc định"
          options={RATE_OPTIONS}
          initial={
            settings
              ? snapToOption(RATE_OPTIONS, settings.playbackRate).value
              : DEFAULT_PLAYBACK_RATE
          }
          disabled={disabled}
          onSave={(playbackRate) => persist({ playbackRate })}
        />
        <AutoSaveSelect
          label="Số lần lặp"
          options={REPEAT_OPTIONS}
          initial={settings ? settings.repeat : DEFAULT_REPEAT}
          disabled={disabled}
          onSave={(repeat) => persist({ repeat })}
        />
        <AutoSaveSelect
          label="Thời gian ghi"
          options={RECORD_FACTOR_OPTIONS}
          initial={
            settings
              ? snapToOption(RECORD_FACTOR_OPTIONS, settings.recordFactor).value
              : DEFAULT_RECORD_FACTOR
          }
          disabled={disabled}
          onSave={(recordFactor) => persist({ recordFactor })}
        />
      </div>
      <LockedAccentRow />
    </>
  );
}

function PracticeSkeleton() {
  return (
    <div className={GRID_CLASS} aria-busy="true" aria-label="Đang tải cài đặt">
      {["a", "b", "c"].map((key) => (
        <div key={key} className="flex flex-col gap-1.5">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-11 w-full" />
        </div>
      ))}
    </div>
  );
}

/** Mục `Luyện tập` của S8: ba mặc định tự lưu và dòng giọng mục tiêu cố định. */
export function PracticeDefaults() {
  const headingId = useId();
  const settings = useSettings();

  let body;
  if (settings.data) {
    body = <PracticeForm settings={settings.data} />;
  } else if (settings.isError) {
    body = (
      <>
        <div
          role="status"
          className="flex flex-wrap items-center gap-3 text-sm font-semibold text-destructive-text"
        >
          <span>{LOAD_FAILED}</span>
          <Button variant="outline" onClick={() => void settings.refetch()}>
            Tải lại
          </Button>
        </div>
        <PracticeForm settings={null} />
      </>
    );
  } else {
    body = <PracticeSkeleton />;
  }

  return (
    <section className={SETTINGS_SECTION_CLASS} aria-labelledby={headingId}>
      <h2 id={headingId} className="text-lg font-bold leading-tight">
        Luyện tập
      </h2>
      {body}
    </section>
  );
}
