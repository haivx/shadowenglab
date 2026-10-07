import type { ReactNode } from "react";
import { Alert, AlertAction } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

export type BannerVariant = "warning" | "error" | "neutral";

/**
 * Banner hệ thống của S1 (components.md): warning · error · neutral.
 * Không đóng được và không chặn thao tác nào khác (SET-02). `Alert` lo role:
 * error = `alert`, warning/neutral = `status`.
 */
export function Banner({
  variant,
  action,
  className,
  children,
}: {
  variant: BannerVariant;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Alert
      variant={variant}
      className={cn(
        "rounded-xl px-4 py-3.5",
        variant === "neutral" &&
          "bg-[color:var(--slate-2)] text-muted-foreground",
        className,
      )}
    >
      <div className="min-w-0 flex-1 leading-[1.5]">{children}</div>
      {action ? <AlertAction>{action}</AlertAction> : null}
    </Alert>
  );
}
