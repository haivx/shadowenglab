import type { Prosody, Scores } from "@shadowenglab/contracts";
import { SCORE_TEXT_CLASS, scoreLevel, scorePercent } from "@/lib/scoreLevel";

interface ScoreHeroProps {
  scores: Scores;
  prosody: Pick<Prosody, "speed" | "pitchRange" | "melodyMatch">;
  /** Số "Lượt k" hiển thị cho kết quả này. */
  attemptLabel: number;
}

interface IndexItem {
  value: number;
  label: string;
  /** Tên đầy đủ (REQ PRO-02) cho `title` và `aria-label`. */
  fullName: string;
}

/**
 * Khối điểm của S3 (UI-SPEC "ScoreHero"): số lớn `overall` + ba chỉ số ngữ điệu.
 * Mỗi số tự có màu qua `scoreLevel()` trên số nguyên đang hiển thị; không có dấu %.
 * Chưa có cột thứ tư "âm" ở P2 (D-07): `scores.sound` luôn null và Phase 5 mới thêm cột đó,
 * nên không có chỗ giữ chỗ nào ở đây.
 */
export function ScoreHero({ scores, prosody, attemptLabel }: ScoreHeroProps) {
  const indices: IndexItem[] = [
    { value: prosody.speed, label: "tốc độ", fullName: "Tốc độ" },
    { value: prosody.pitchRange, label: "lên xuống", fullName: "Độ lên xuống" },
    {
      value: prosody.melodyMatch,
      label: "giai điệu",
      fullName: "Khớp giai điệu",
    },
  ];

  return (
    <section
      aria-label={`Điểm lượt ${attemptLabel}`}
      className="flex flex-wrap items-end gap-7 border-t border-border pt-6"
    >
      <div className="flex flex-col">
        <span
          className={`text-[72px] font-extrabold leading-[0.9] tracking-[-0.04em] [font-variant-numeric:tabular-nums] ${SCORE_TEXT_CLASS[scoreLevel(scores.overall)]}`}
        >
          {scorePercent(scores.overall)}
        </span>
        <span className="mt-1.5 text-[13px] leading-[1.45] text-muted-foreground">
          giống bản gốc
        </span>
      </div>
      <div className="flex gap-6 pb-1">
        {indices.map((item) => (
          <div
            key={item.label}
            role="group"
            title={item.fullName}
            aria-label={`${item.fullName} ${scorePercent(item.value)} phần trăm`}
            className="flex flex-col"
          >
            <span
              className={`text-[24px] font-bold leading-[1.2] [font-variant-numeric:tabular-nums] ${SCORE_TEXT_CLASS[scoreLevel(item.value)]}`}
            >
              {scorePercent(item.value)}
            </span>
            <span className="text-xs text-muted-foreground">{item.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
