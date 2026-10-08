import type { Word } from "@shadowenglab/contracts";
import { ipaLine } from "@/lib/ipaLine";

const HELPER_TEXT =
  "Nhận dạng tự động từ chính giọng người nói trong video, không lấy từ điển. Từ nào chưa chắc sẽ hiện “—”.";

interface SpokenIpaProps {
  /** Từ của câu hiện tại; chỉ `Word.ipa` (nhận dạng từ audio mẫu) được hiển thị (D-14). */
  words: readonly Word[];
}

/**
 * Khối IPA của câu đang tập (UI-SPEC S3 mục 3, E10, G9): badge `IPA từ audio mẫu`,
 * dòng IPA `/…/` với `—` cho từ chưa chắc, và ghi chú. Dòng IPA xuống dòng khi dài.
 */
export function SpokenIpa({ words }: SpokenIpaProps) {
  const { text, allMissing } = ipaLine(words);
  return (
    <section
      aria-label="IPA từ audio mẫu"
      className="flex flex-col items-start gap-2"
    >
      <span className="inline-flex items-center gap-2 rounded-sm bg-original-soft px-2 py-0.5 text-xs font-bold text-original-text">
        <span aria-hidden="true" className="size-2 rounded-full bg-original" />
        IPA từ audio mẫu
      </span>
      {allMissing ? (
        <p className="m-0 text-base leading-[1.4] text-muted-foreground">
          Chưa nhận dạng chắc câu này.
        </p>
      ) : (
        <p className="m-0 break-words font-ipa text-base leading-[1.4] text-[color:var(--teal-12)]">
          {text}
        </p>
      )}
      <p className="m-0 text-xs text-muted-foreground">{HELPER_TEXT}</p>
    </section>
  );
}
