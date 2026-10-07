"use client";

import { useLessons } from "@/lib/queries";

export default function LibraryPage() {
  const { data, error, isPending } = useLessons();

  return (
    <main>
      <h1>Thư viện</h1>
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
  );
}
