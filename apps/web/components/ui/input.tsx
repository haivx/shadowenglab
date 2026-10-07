import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Cao 44, bo 8, viền `--input` (ô URL cao 48 qua `className="h-12"`).
 * Lỗi: `aria-invalid` đổi viền 2px destructive.
 */
function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-11 w-full min-w-0 rounded border border-input bg-card px-3.5 text-sm text-foreground transition-colors [transition-duration:120ms] placeholder:text-muted-foreground focus-visible:border-foreground disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-2 aria-[invalid=true]:border-destructive",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
