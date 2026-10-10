"use client";

import type { ModelStatuses } from "@shadowenglab/contracts";
import Link from "next/link";
import { Banner } from "@/components/Banner";
import { Button } from "@/components/ui/button";
import { useMicPermission } from "@/lib/audio/micPermission";
import { useLessons, useSystemStatus } from "@/lib/queries";

const MODEL_NAMES: Record<keyof ModelStatuses, string> = {
  demucs: "Demucs",
  whisper: "mlx-whisper",
  wav2vec2: "wav2vec2-espeak",
};

function Mono({ children }: { children: string }) {
  return <code className="font-mono text-[13px]">{children}</code>;
}

function modelNames(
  models: ModelStatuses,
  state: ModelStatuses[keyof ModelStatuses],
): string[] {
  return (Object.keys(MODEL_NAMES) as (keyof ModelStatuses)[])
    .filter((key) => models[key] === state)
    .map((key) => MODEL_NAMES[key]);
}

/**
 * Chồng banner của S1 theo thứ tự UI-SPEC: thiếu model, model đang nạp, chưa có
 * key, micro bị chặn, mất kết nối backend. Không banner nào đóng được và không
 * banner nào vô hiệu hoá tạo bài hay luyện tập (D-13, SET-01, SET-02).
 * Trước phản hồi đầu tiên của system-status thì không hiện gì.
 */
export function SystemBanners() {
  const status = useSystemStatus();
  const lessons = useLessons();
  const mic = useMicPermission();

  const backendDown = status.isError || lessons.isError;
  const system = status.data;

  const missing = system ? modelNames(system.models, "missing") : [];
  const loading = system ? modelNames(system.models, "loading") : [];

  const banners = [];

  if (missing.length > 0) {
    banners.push(
      <Banner key="models-missing" variant="error">
        Chưa có model: {missing.join(", ")}. Chạy <Mono>make setup</Mono> rồi
        khởi động lại <Mono>make dev</Mono>.
      </Banner>,
    );
  }

  if (loading.length > 0) {
    banners.push(
      <Banner key="models-loading" variant="neutral">
        Model đang nạp… Bạn vẫn tập được các bài đã có.
      </Banner>,
    );
  }

  if (system && !system.hasKey) {
    banners.push(
      <Banner
        key="no-key"
        variant="warning"
        action={
          <Link
            href="/settings"
            className="font-semibold text-warning-text underline underline-offset-2"
          >
            Thêm key
          </Link>
        }
      >
        Chưa có OpenAI key: chưa dịch được câu mới. Chấm điểm vẫn chạy bình
        thường.
      </Banner>,
    );
  }

  if (system && mic === "denied") {
    banners.push(
      <Banner key="mic-denied" variant="warning">
        Trình duyệt đang chặn micro. Cho phép micro cho localhost:3000 trong cài
        đặt trình duyệt, rồi tải lại trang.
      </Banner>,
    );
  }

  if (backendDown) {
    banners.push(
      <Banner
        key="backend-down"
        variant="error"
        action={
          <Button
            variant="outline"
            onClick={() => {
              void status.refetch();
              void lessons.refetch();
            }}
          >
            Tải lại
          </Button>
        }
      >
        Không kết nối được backend. Chạy <Mono>make dev</Mono> rồi bấm Tải lại.
      </Banner>,
    );
  }

  if (banners.length === 0) return null;
  return <div className="flex flex-col gap-3">{banners}</div>;
}
