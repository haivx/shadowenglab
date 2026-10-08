"use client";

import type { OpenAiKeyCheckResult } from "@shadowenglab/contracts";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiRequestError, checkOpenAiKey } from "@/lib/api";
import { queryKeys, useSystemStatus } from "@/lib/queries";
import { SETTINGS_SECTION_CLASS } from "@/lib/settingsForm";
import { cn } from "@/lib/utils";

const RESULT_VALID = "Key hợp lệ · đã lưu";
const RESULT_INVALID = "Key không hợp lệ · chưa lưu";
const RESULT_NETWORK =
  "Không kiểm tra được (không có mạng). Key chưa được lưu.";
const RESULT_PENDING = "Đang kiểm tra…";
const STATUS_NO_KEY = "Chưa có key";

interface ResultLine {
  text: string;
  tone: "success" | "destructive" | "muted";
}

function resultLine(result: OpenAiKeyCheckResult): ResultLine {
  if (result.valid === true) return { text: RESULT_VALID, tone: "success" };
  if (result.valid === false) {
    // Ô trống và chưa lưu key nào: không có gì để kiểm tra, không phải "key sai".
    return result.reason === "no_key"
      ? { text: STATUS_NO_KEY, tone: "muted" }
      : { text: RESULT_INVALID, tone: "destructive" };
  }
  return { text: RESULT_NETWORK, tone: "muted" };
}

const TONE_CLASS: Record<ResultLine["tone"], string> = {
  success: "text-success-text",
  destructive: "text-destructive-text",
  muted: "text-muted-foreground",
};

/**
 * Mục `API key` của S8 (D-11, SET-03). Key gõ vào chỉ nằm trong state của component:
 * không log, không lưu client, xoá khỏi ô sau khi lưu thành công. Backend chỉ trả `maskedKey`
 * (hiện làm placeholder). Ô trống + đã có key = kiểm tra key đã lưu.
 */
export function KeyField() {
  const inputId = useId();
  const queryClient = useQueryClient();
  const status = useSystemStatus();
  const [apiKey, setApiKey] = useState("");

  const check = useMutation({
    mutationFn: (typed: string) =>
      checkOpenAiKey(typed === "" ? undefined : typed),
    onSuccess: (result) => {
      if (result.valid === true && result.saved) {
        setApiKey("");
        // Banner "Chưa có OpenAI key" ở S1 phải biến mất (và maskedKey được làm mới).
        void queryClient.invalidateQueries({
          queryKey: queryKeys.systemStatus,
        });
      }
    },
  });

  const hasKey = status.data?.hasKey;
  const noKeyAtAll = hasKey === false && apiKey.trim() === "";

  let line: ResultLine | null = null;
  if (check.isPending) {
    line = { text: RESULT_PENDING, tone: "muted" };
  } else if (check.isError) {
    const message =
      check.error instanceof ApiRequestError ? check.error.message : null;
    line = {
      text: message ?? RESULT_NETWORK,
      tone: message === null ? "muted" : "destructive",
    };
  } else if (check.data) {
    line = resultLine(check.data);
  } else if (hasKey === false) {
    line = { text: STATUS_NO_KEY, tone: "muted" };
  }

  return (
    <section
      className={SETTINGS_SECTION_CLASS}
      aria-labelledby={`${inputId}-h`}
    >
      <div className="flex flex-col gap-1">
        <h2 id={`${inputId}-h`} className="text-lg font-bold leading-tight">
          API key
        </h2>
        <span className="text-sm text-muted-foreground">
          Lưu trong <code className="font-mono text-[13px]">.env</code> trên
          máy. Chấm điểm không cần key.
        </span>
      </div>
      <form
        className="flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (!check.isPending && !noKeyAtAll) check.mutate(apiKey.trim());
        }}
      >
        <Label htmlFor={inputId}>
          OpenAI · gợi ý bằng LLM và đọc chậm (TTS)
        </Label>
        <div className="flex flex-wrap gap-2">
          <Input
            id={inputId}
            type="password"
            autoComplete="new-password"
            spellCheck={false}
            value={apiKey}
            placeholder={status.data?.maskedKey ?? ""}
            onChange={(event) => {
              setApiKey(event.target.value);
              if (!check.isPending) check.reset();
            }}
            className="flex-[1_1_280px] font-mono text-sm"
          />
          <Button
            type="submit"
            variant="outline"
            disabled={check.isPending || noKeyAtAll}
          >
            Kiểm tra
          </Button>
        </div>
        <span
          role="status"
          className={cn(
            "min-h-[1.25rem] text-[13px] font-semibold",
            line ? TONE_CLASS[line.tone] : "",
          )}
        >
          {line?.text}
        </span>
      </form>
    </section>
  );
}
