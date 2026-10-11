"use client";

import { Settings } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

/**
 * Header S1/S8 (UI-SPEC): logo + `Thư viện` + icon Settings.
 * P1 không có `Ôn luyện` / `Tiến bộ` (chưa có route, G5).
 */
export function AppHeader() {
  const pathname = usePathname();
  const inLibrary = pathname === "/";

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border bg-card px-8 py-3">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-lg font-extrabold tracking-[-0.02em] text-foreground hover:text-muted-foreground"
      >
        <Image
          src="/LOGO-2-512x512.png"
          alt=""
          width={32}
          height={32}
          priority
          className="size-8"
        />
        ShadowEngLab
      </Link>
      <nav aria-label="Điều hướng chính" className="flex items-center gap-1">
        <Link
          href="/"
          aria-current={inLibrary ? "page" : undefined}
          className={cn(
            "inline-flex h-10 items-center rounded px-3.5 text-[15px] font-semibold text-foreground transition-colors [transition-duration:120ms] hover:bg-muted",
            inLibrary && "bg-muted",
          )}
        >
          Thư viện
        </Link>
        <Link
          href="/settings"
          aria-label="Settings"
          className="inline-flex h-10 w-11 items-center justify-center rounded text-foreground transition-colors [transition-duration:120ms] hover:bg-muted"
        >
          <Settings aria-hidden="true" className="size-5" strokeWidth={2} />
        </Link>
      </nav>
    </header>
  );
}
