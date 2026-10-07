"use client";

import type { CSSProperties } from "react";
import { Toaster as Sonner, type ToasterProps } from "sonner";

/**
 * Toast lỗi backend (flows.md): góc trên bên phải, viền 1px, không shadow.
 * Không có dark mode nên không dùng next-themes (không thêm package ngoài danh sách duyệt).
 */
function Toaster(props: ToasterProps) {
  return (
    <Sonner
      theme="light"
      position="top-right"
      className="toaster group"
      style={
        {
          "--normal-bg": "var(--card)",
          "--normal-text": "var(--foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius-lg)",
        } as CSSProperties
      }
      toastOptions={{
        classNames: {
          toast: "!shadow-none border border-border font-sans",
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
