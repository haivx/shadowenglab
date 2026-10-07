"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { AppHeader } from "@/components/AppHeader";
import { LessonCard } from "@/components/LessonCard";
import { SystemBanners } from "@/components/SystemBanners";
import { Button } from "@/components/ui/button";
import { librarySummary } from "@/lib/lessonView";
import { useLessons } from "@/lib/queries";

export default function LibraryPage() {
  const { data } = useLessons();
  const items = data ?? [];
  const summary = librarySummary(items);

  return (
    <>
      <AppHeader />
      <main className="mx-auto flex max-w-[1360px] flex-col gap-6 p-8">
        <SystemBanners />
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-[34px] font-extrabold leading-tight tracking-[-0.03em]">
              Thư viện
            </h1>
            {summary ? (
              <p className="text-[15px] text-muted-foreground">{summary}</p>
            ) : null}
          </div>
          <Button asChild size="lg">
            <Link href="/?create=1">
              <Plus aria-hidden="true" />
              Tạo bài từ YouTube
            </Link>
          </Button>
        </div>
        <ul className="grid list-none grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-4">
          {items.map((item) => (
            <li key={item.lesson.id} className="flex flex-col">
              <LessonCard item={item} />
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}
