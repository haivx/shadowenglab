"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { LessonCard } from "@/components/LessonCard";
import { SystemBanners } from "@/components/SystemBanners";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { filterByTab, librarySummary, type LibraryTab } from "@/lib/lessonView";
import { useLessons } from "@/lib/queries";

const GRID_CLASS =
  "grid list-none grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-4";

const SKELETON_KEYS = ["a", "b", "c"] as const;

function CreateLessonButton() {
  return (
    <Button asChild size="lg">
      <Link href="/?create=1">
        <Plus aria-hidden="true" />
        Tạo bài từ YouTube
      </Link>
    </Button>
  );
}

/** Thẻ khung xương khi tải lần đầu: khối 16:9 + 3 dòng, nền muted. */
function SkeletonCard() {
  return (
    <Card className="gap-0 p-0">
      <Skeleton className="aspect-video w-full rounded-none" />
      <div className="flex flex-col gap-2.5 p-4">
        <Skeleton className="h-4 w-4/5" />
        <Skeleton className="h-3.5 w-3/5" />
        <Skeleton className="h-3.5 w-2/5" />
      </div>
    </Card>
  );
}

export default function LibraryPage() {
  const { data, isPending } = useLessons();
  const [tab, setTab] = useState<LibraryTab>("all");

  const items = data ?? [];
  const visible = filterByTab(items, tab);
  const summary = librarySummary(items);

  let body;
  if (data === undefined) {
    // Lần tải đầu: khung xương. Nếu lỗi, banner mất kết nối lo phần giải thích.
    body = isPending ? (
      <ul
        className={GRID_CLASS}
        aria-busy="true"
        aria-label="Đang tải thư viện"
      >
        {SKELETON_KEYS.map((key) => (
          <li key={key} className="flex flex-col">
            <SkeletonCard />
          </li>
        ))}
      </ul>
    ) : null;
  } else if (items.length === 0) {
    body = (
      <div className="flex flex-col items-center gap-4 px-4 py-16 text-center">
        <h2 className="text-lg font-bold leading-[1.2]">Chưa có bài nào</h2>
        <p className="text-sm text-muted-foreground">
          Dán link YouTube để tạo bài đầu tiên.
        </p>
        <CreateLessonButton />
      </div>
    );
  } else if (visible.length === 0) {
    body = (
      <p className="px-4 py-16 text-center text-sm text-muted-foreground">
        Chưa có bài nào ở mục này.
      </p>
    );
  } else {
    body = (
      <ul className={GRID_CLASS}>
        {visible.map((item) => (
          <li key={item.lesson.id} className="flex flex-col">
            <LessonCard item={item} />
          </li>
        ))}
      </ul>
    );
  }

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
          <CreateLessonButton />
        </div>
        <Tabs
          value={tab}
          onValueChange={(value) => setTab(value as LibraryTab)}
          className="gap-6"
        >
          <TabsList aria-label="Lọc bài theo tiến độ tập">
            <TabsTrigger value="all">Tất cả</TabsTrigger>
            <TabsTrigger value="practicing">Đang tập</TabsTrigger>
            <TabsTrigger value="done">Đã xong</TabsTrigger>
          </TabsList>
          <TabsContent value={tab}>{body}</TabsContent>
        </Tabs>
      </main>
    </>
  );
}
