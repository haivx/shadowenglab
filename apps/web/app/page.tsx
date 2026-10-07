"use client";

import { AppHeader } from "@/components/AppHeader";
import { useLessons } from "@/lib/queries";

export default function LibraryPage() {
  const { data, error, isPending } = useLessons();

  return (
    <>
      <AppHeader />
      <main className="mx-auto flex max-w-[1360px] flex-col gap-6 p-8">
        <h1 className="text-[34px] font-extrabold leading-tight tracking-[-0.03em]">
          Thư viện
        </h1>
        {isPending ? <p>Đang tải…</p> : null}
        {error ? <p role="alert">{error.message}</p> : null}
        <ul>
          {data?.map((item) => (
            <li key={item.lesson.id}>
              {item.lesson.title} ({item.lesson.status})
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}
