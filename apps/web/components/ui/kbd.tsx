import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Gợi ý phím tắt (components.md Kbd): JetBrains Mono 11, padding 3/6, bo 6,
 * nền muted, vạch đáy slate-6 như kbd trong mock S3.
 */
function Kbd({ className, ...props }: React.ComponentProps<"kbd">) {
  return (
    <kbd
      data-slot="kbd"
      className={cn(
        "inline-flex items-center rounded-sm bg-muted px-1.5 py-[3px] font-mono text-[11px] font-medium leading-none text-muted-foreground shadow-[inset_0_-1px_0_var(--slate-6)]",
        className,
      )}
      {...props}
    />
  );
}

export { Kbd };
