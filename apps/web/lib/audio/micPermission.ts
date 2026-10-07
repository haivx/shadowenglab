"use client";

import { useEffect, useState } from "react";

export type MicPermission = "granted" | "denied" | "prompt" | "unknown";

function toMicPermission(state: PermissionState): MicPermission {
  return state === "granted" || state === "denied" || state === "prompt"
    ? state
    : "unknown";
}

/**
 * Quyền micro của trình duyệt qua Permissions API, cập nhật khi người dùng đổi.
 * Thiếu API (hoặc truy vấn `microphone` ném lỗi, ví dụ Safari/Firefox cũ) thì
 * trả `unknown` và không có banner nào (RESEARCH A10: chỉ báo khi chắc chắn).
 */
export function useMicPermission(): MicPermission {
  const [permission, setPermission] = useState<MicPermission>("unknown");

  useEffect(() => {
    let cancelled = false;
    let status: PermissionStatus | undefined;
    const onChange = () => {
      if (status && !cancelled) setPermission(toMicPermission(status.state));
    };

    async function watch() {
      try {
        if (
          typeof navigator === "undefined" ||
          !navigator.permissions ||
          typeof navigator.permissions.query !== "function"
        ) {
          return;
        }
        const result = await navigator.permissions.query({
          name: "microphone" as PermissionName,
        });
        if (cancelled) return;
        status = result;
        setPermission(toMicPermission(result.state));
        result.onchange = onChange;
      } catch {
        if (!cancelled) setPermission("unknown");
      }
    }
    void watch();

    return () => {
      cancelled = true;
      if (status) status.onchange = null;
    };
  }, []);

  return permission;
}
