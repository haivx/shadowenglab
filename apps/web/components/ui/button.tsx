import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import { Kbd } from "@/components/ui/kbd";
import { cn } from "@/lib/utils";

/**
 * Biến thể theo design (components.md Button): solid · soft-original · soft-you ·
 * outline · ghost. Hover dùng token tường minh, không dùng modifier độ mờ trên
 * màu var() (UI-SPEC Token Implementation Map mục 4). Viền focus do `:focus-visible`
 * toàn cục trong globals.css đảm nhiệm.
 */
const buttonVariants = cva(
  "inline-flex shrink-0 select-none items-center justify-center gap-2 whitespace-nowrap rounded border border-transparent font-semibold transition-colors [transition-duration:120ms] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        solid:
          "bg-primary text-primary-foreground hover:bg-[color:var(--slate-11)]",
        "soft-original":
          "bg-original-soft text-original-text hover:border-original",
        "soft-you": "bg-you-soft text-you-text hover:border-you",
        outline: "border-input bg-card text-foreground hover:bg-muted",
        ghost: "text-foreground hover:bg-muted",
      },
      size: {
        md: "h-11 px-4 text-sm [&_svg]:size-4",
        lg: "h-12 px-5 text-[15px] [&_svg]:size-[18px]",
        icon: "size-11 [&_svg]:size-5",
      },
    },
    defaultVariants: { variant: "solid", size: "md" },
  },
);

type ButtonVariant = NonNullable<
  VariantProps<typeof buttonVariants>["variant"]
>;

type ButtonBaseProps = Omit<React.ComponentProps<"button">, "children"> & {
  variant?: ButtonVariant;
  asChild?: boolean;
  /** Gợi ý phím tắt hiển thị trong nút (ví dụ "R"). */
  kbd?: string;
  children?: React.ReactNode;
};

/** Nút chỉ có icon bắt buộc `aria-label` và `title` (chứa phím tắt nếu có). */
type IconButtonProps = ButtonBaseProps & {
  size: "icon";
  "aria-label": string;
  title: string;
};

type LabelledButtonProps = ButtonBaseProps & { size?: "md" | "lg" };

type ButtonProps = IconButtonProps | LabelledButtonProps;

function Button({
  className,
  variant = "solid",
  size = "md",
  asChild = false,
  kbd,
  type = "button",
  children,
  ...props
}: ButtonProps) {
  const classes = cn(buttonVariants({ variant, size }), className);

  if (asChild) {
    return (
      <Slot.Root
        data-slot="button"
        data-variant={variant}
        data-size={size}
        className={classes}
        {...props}
      >
        {children}
      </Slot.Root>
    );
  }

  return (
    <button
      data-slot="button"
      data-variant={variant}
      data-size={size}
      type={type}
      className={classes}
      {...props}
    >
      {children}
      {kbd ? <Kbd aria-hidden="true">{kbd}</Kbd> : null}
    </button>
  );
}

export { Button, buttonVariants };
export type { ButtonProps, ButtonVariant };
