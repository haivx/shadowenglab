# Gap Phase 3: gợi ý phong phú hơn (đề xuất để Liam duyệt)

Ngày: 2026-10-10 · Nguồn: phản hồi UAT của Liam ("chỉ có 1 nhận xét, cần đa dạng hơn") · Phạm vi đã chọn: **A + B**, gap-closure Phase 3.

## Vì sao hiện chỉ thấy 1 câu

1. Tip chỉ sinh từ issue (mỗi tip trỏ `issueRef`); rule ưu tiên precision nên lượt đó chỉ có 1 issue chắc chắn (`FLAT_PITCH`). D-14: mỗi mã tối đa 1 tip.
2. Mỗi mã chỉ có 1 câu cố định, không dùng số đo đã có trong `issue.data`.

Không đổi: contract (`Issue`, `Tip`), ngưỡng, rule, D-15 (không có issue → câu nhận xét phía client). Không tăng số issue tìm được.

## A. Template dùng số đo + nhiều cách nói

- Mỗi mã có 3–4 biến thể. Biến thể chọn **xác định** theo `(segmentIndex + attempt − 1) mod n`: cùng lượt luôn ra cùng câu (đọc lại lượt cũ không đổi chữ), lượt sau của cùng câu đổi cách nói.
- Số chèn vào lấy từ `issue.data` có sẵn; "nửa cung" = semitone, làm tròn 0.5; % làm tròn tới 5.
- `*từ*` vẫn là dấu gạch chân, từ vẫn bị lọc `*` (T-03-14).

### FLAT_PITCH (`pitchRange` → `{pct}` = round(pitchRange·100 / 5)·5)
1. Độ lên xuống của bạn chỉ bằng khoảng {pct}% bản gốc; mở rộng giọng, lên cao và xuống thấp rõ hơn.
2. Giọng còn phẳng (khoảng {pct}% độ lên xuống của bản gốc). Nghe lại bản gốc và bắt chước chỗ giọng vút lên, hạ xuống.
3. Thử phóng đại ngữ điệu một chút: bạn mới lên xuống được khoảng {pct}% so với bản gốc.
4. Bản gốc lên xuống nhiều hơn bạn (bạn ≈ {pct}%); đừng ngại đọc hơi "quá", thường sẽ vừa.

### EXTRA_PAUSE (`wordIndex` → `{word}`, `userMs` → `{ms}`)
1. Đọc liền qua *{word}*, đừng ngắt ({ms} ms).
2. Bạn dừng {ms} ms sau *{word}*, bản gốc đọc nối luôn; nối *{word}* với từ sau.
3. Bỏ khoảng nghỉ sau *{word}* ({ms} ms): giữ hơi và đọc trọn cụm.

### FINAL_CONTOUR (từ cuối `{last}`)
Bản gốc xuống giọng:
1. Xuống giọng ở cuối câu, ở *{last}*; bạn đang lên giọng.
2. Cuối câu bản gốc hạ giọng ở *{last}*, còn bạn lại lên nên nghe như đang hỏi. Kết thúc dứt khoát, hạ xuống.
3. Ở *{last}*, để giọng rơi xuống như kết thúc một ý, đừng kéo lên.

Bản gốc lên giọng:
1. Lên giọng ở cuối câu, ở *{last}*; bạn đang xuống giọng.
2. Bản gốc kéo giọng lên ở *{last}* (giọng hỏi hoặc chưa nói hết ý), bạn lại hạ xuống; kết thúc bằng giọng đi lên.
3. Ở *{last}*, nâng giọng lên ở cuối như bản gốc thay vì hạ xuống.

### PITCH_DEVIATION (`wordIndex` → `{word}`, |`meanDiffSt`| → `{st}`)
Cao hơn:
1. Bạn đang đọc cao hơn bản gốc ở *{word}*; hạ giọng xuống.
2. *{word}* của bạn cao hơn bản gốc khoảng {st} nửa cung; đọc từ này thấp và nhẹ hơn.
3. Hạ *{word}* xuống chừng {st} nửa cung cho khớp bản gốc.

Thấp hơn:
1. Bạn đang đọc thấp hơn bản gốc ở *{word}*; nâng giọng lên.
2. *{word}* của bạn thấp hơn bản gốc khoảng {st} nửa cung; đẩy giọng lên ở từ này.
3. Nâng *{word}* lên chừng {st} nửa cung, bản gốc nói từ này cao hơn.

### STRESS_MISMATCH (`{ref}`, `{user}`)
1. Nhấn vào *{ref}*, không phải *{user}*.
2. Bản gốc nhấn mạnh nhất ở *{ref}*, bạn lại nhấn *{user}*. Đọc *{ref}* to, dài và cao hơn một chút.
3. Dồn trọng âm của câu về *{ref}*; *{user}* nên đọc nhẹ đi.

## B. Nới D-14

- Lượt 1: mỗi mã một tip theo thứ tự ưu tiên cũ (`STRESS_MISMATCH > FINAL_CONTOUR > EXTRA_PAUSE > PITCH_DEVIATION > FLAT_PITCH`), cùng mã lấy issue lệch nhiều nhất.
- Lượt 2 (nếu còn chỗ): issue lệch nhiều thứ hai của các mã theo từ (`EXTRA_PAUSE`, `PITCH_DEVIATION`), cùng thứ tự ưu tiên; không lặp lại cùng một từ.
- Vẫn tối đa 3 tip, mỗi mã tối đa 2. Mã mức câu (`STRESS_MISMATCH`, `FINAL_CONTOUR`, `FLAT_PITCH`) vốn chỉ có 1 issue.

## Hệ quả

- Lượt chỉ có 1 issue vẫn chỉ có 1 tip (đúng precision trước recall); A làm câu đó cụ thể hơn. Lượt có nhiều lỗi theo từ được 2–3 tip.
- Cần truyền `segmentIndex` và `attempt` vào `select_tips` (đã có ở thời điểm dựng `ScoreResult`, C1).
- Lời văn cuối cùng vẫn được review ở PR (P3-G18).

## C'. Mở rộng D-15: không có issue nhưng chỉ số thấp (Liam chọn 2026-10-10, sau UAT ảnh #5)

Bối cảnh: lượt 69 điểm (tốc độ 82, lên xuống 64, giai điệu 60) không có issue chắc chắn nên chỉ hiện "Chưa thấy lỗi cụ thể nào chắc chắn; nghe lại bản gốc rồi thử lại." Liam: điểm thấp thì phải có nhận xét.

- Phía client, không đổi contract, `tips` vẫn rỗng (chỉ tip mới phải có `issueRef`). Đây là **câu nhận xét theo chỉ số**, hiển thị ở đúng chỗ câu D-15 hiện nay, không gắn nhãn "AI", không trỏ vào từ cụ thể (chưa đủ chắc).
- Điều kiện: không có issue **và** ít nhất một trong ba chỉ số hiển thị (làm tròn như ScoreHero) < 80. Lấy tối đa 2 chỉ số thấp nhất (< 80), thấp nhất trước. Không có chỉ số nào < 80 → giữ câu khen D-15 như cũ.
- Mỗi chỉ số 3 cách nói, chọn theo cùng quy tắc `(segmentIndex + attempt − 1) mod 3`. `{v}` = điểm hiển thị của chỉ số đó (số nguyên, như ScoreHero).
- Câu chữ trung tính về hướng: `speed` và `pitchRange` là `min(r, 1/r)` nên không biết nhanh/chậm, rộng/hẹp.

### Giai điệu (melodyMatch)
1. Giai điệu mới khớp {v}%: nghe lại bản gốc, chú ý chỗ giọng đi lên, đi xuống rồi bắt chước đúng hướng.
2. Đường lên xuống của bạn còn khác bản gốc (khớp {v}%). Mở So sánh ngữ điệu để xem đoạn lệch rồi đọc lại.
3. Đọc lại từng cụm theo bản gốc, bám chỗ giọng lên và xuống; giai điệu hiện khớp {v}%.

### Lên xuống (pitchRange)
1. Độ lên xuống mới khớp {v}% với bản gốc; nghe lại xem bản gốc lên cao, xuống thấp tới đâu rồi bắt chước đúng mức đó.
2. Biên độ giọng của bạn khác bản gốc (khớp {v}%). Mở So sánh ngữ điệu để so độ cao thấp của hai đường.
3. Bám theo độ cao thấp của bản gốc ở từng cụm; độ lên xuống hiện khớp {v}%.

### Tốc độ (speed)
1. Nhịp đọc của bạn còn lệch bản gốc (khớp {v}%); đọc cùng lúc với bản gốc để bắt nhịp.
2. Tốc độ khớp {v}%: nghe lại bản gốc, để ý độ dài các khoảng nghỉ rồi đọc theo đúng nhịp đó.
3. Nhại sát theo bản gốc, gần như cùng lúc, để tốc độ khớp hơn; hiện khớp {v}%.

Lời văn C' do Claude soạn sau khi Liam chọn cơ chế; review ở PR (P3-G18).
