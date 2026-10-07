"use client";

import * as React from "react";
import { Progress as ProgressPrimitive } from "radix-ui";
import { cn } from "@/lib/utils";

type ProgressProps = Omit<
  React.ComponentProps<typeof ProgressPrimitive.Root>,
  "value"
> & {
  /** 0..100. Bỏ qua khi `indeterminate`. */
  value?: number;
  /** Bước đang chạy không có phần trăm (contract không có %, G17). */
  indeterminate?: boolean;
};

/**
 * Cao 6, bo 3, nền muted, phần đầy = foreground. `indeterminate`: thanh chạy;
 * khi người dùng giảm chuyển động, thành thanh tĩnh đầy một nửa (UI-SPEC).
 */
function Progress({
  className,
  value = 0,
  indeterminate = false,
  ...props
}: ProgressProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      value={indeterminate ? null : clamped}
      className={cn(
        "relative h-1.5 w-full overflow-hidden rounded-[3px] bg-muted",
        className,
      )}
      {...props}
    >
      {indeterminate ? (
        <ProgressPrimitive.Indicator
          data-slot="progress-indicator"
          className="h-full w-2/5 rounded-[3px] bg-foreground motion-safe:animate-progress-slide motion-reduce:w-1/2"
        />
      ) : (
        <ProgressPrimitive.Indicator
          data-slot="progress-indicator"
          className="h-full w-full rounded-[3px] bg-foreground transition-transform [transition-duration:120ms]"
          style={{ transform: `translateX(-${100 - clamped}%)` }}
        />
      )}
    </ProgressPrimitive.Root>
  );
}

export { Progress };
