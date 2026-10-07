"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  // Một QueryClient cho mỗi lần mount (tránh chia sẻ cache giữa request SSR).
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 0, retry: 1 } },
      }),
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
