"use client";

import { useParams } from "next/navigation";
import { PracticeRoom } from "@/components/PracticeRoom";

/** S3 Phòng tập: /lessons/{id}. Chỉ bài `ready` mới được liên kết tới đây từ S1. */
export default function LessonPage() {
  const params = useParams<{ id: string }>();
  const raw = params.id;
  const id = Array.isArray(raw) ? raw[0] : raw;
  return <PracticeRoom lessonId={id ?? ""} />;
}
