import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Nền của `Banner` (components.md): warning · error · neutral. Không chặn thao tác.
 * `role="status"` cho warning/neutral, `role="alert"` cho error (UI-SPEC Component Inventory).
 */
const alertVariants = cva(
  "flex w-full flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3.5 text-sm",
  {
    variants: {
      variant: {
        warning: "border-warning-border bg-warning-soft text-warning-text",
        error:
          "border-destructive-border bg-destructive-soft text-destructive-text",
        neutral: "border-border bg-muted text-foreground",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

type AlertVariant = NonNullable<VariantProps<typeof alertVariants>["variant"]>;

function Alert({
  className,
  variant = "neutral",
  role,
  ...props
}: React.ComponentProps<"div"> & { variant?: AlertVariant }) {
  return (
    <div
      data-slot="alert"
      data-variant={variant}
      role={role ?? (variant === "error" ? "alert" : "status")}
      className={cn(alertVariants({ variant }), className)}
      {...props}
    />
  );
}

function AlertTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-title"
      className={cn("font-semibold", className)}
      {...props}
    />
  );
}

function AlertDescription({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-description"
      className={cn("text-sm", className)}
      {...props}
    />
  );
}

function AlertAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-action"
      className={cn("flex shrink-0 items-center gap-2", className)}
      {...props}
    />
  );
}

export { Alert, AlertTitle, AlertDescription, AlertAction, alertVariants };
