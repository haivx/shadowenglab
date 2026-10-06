#!/bin/sh
# Kiểm tra tự động `make dev`: FastAPI (127.0.0.1:8000) và Next.js (localhost:3000) cùng lên,
# (tuỳ chọn) bài LESSON_ID đã tạo được API trả về với status "ready", rồi một SIGTERM tới
# process group của `make dev` dừng cả hai và giải phóng cổng.
#
# Dùng: [DATA_DIR=...] [LESSON_ID=<ulid>] sh scripts/dev_smoke.sh
# In "DEV-SMOKE OK" (thoát 0) hoặc "DEV-SMOKE FAIL" cùng 40 dòng log cuối (thoát 1).
#
# Tín hiệu chỉ gửi tới process group của job nền (PID âm), không bao giờ tới pid 0 hay
# group của chính script này (T-01-21).

set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT" || exit 1

LOG=$(mktemp "${TMPDIR:-/tmp}/dev_smoke.XXXXXX")
API_URL="http://127.0.0.1:8000"
WEB_URL="http://localhost:3000/"
TIMEOUT_S=120
JOB_PID=""

fail() {
  echo "DEV-SMOKE FAIL: $1"
  echo "--- 40 dòng log cuối ($LOG) ---"
  tail -n 40 "$LOG"
  stop_job
  exit 1
}

# Dừng đúng process group của `make dev` (nếu còn chạy).
stop_job() {
  if [ -n "$JOB_PID" ] && kill -0 "$JOB_PID" 2>/dev/null; then
    kill -TERM -- "-$JOB_PID" 2>/dev/null
    wait "$JOB_PID" 2>/dev/null
  fi
  JOB_PID=""
}

listening() {
  # In PID đang LISTEN trên cổng $1 (rỗng nếu không có).
  lsof -ti "tcp:$1" -sTCP:LISTEN 2>/dev/null
}

# Cổng phải trống từ đầu, nếu không "lên được" có thể là server của lần chạy khác.
for port in 8000 3000; do
  if [ -n "$(listening "$port")" ]; then
    fail "cổng $port đang bị chiếm trước khi chạy (dừng tiến trình đó rồi chạy lại)"
  fi
done

# Job control: job nền chạy trong process group riêng, id group = PID của job.
set -m
make dev >"$LOG" 2>&1 &
JOB_PID=$!
set +m

api_ok() { curl -sf "$API_URL/health" >/dev/null 2>&1; }
web_ok() { curl -sf -o /dev/null "$WEB_URL" 2>/dev/null; }

elapsed=0
while [ "$elapsed" -lt "$TIMEOUT_S" ]; do
  if ! kill -0 "$JOB_PID" 2>/dev/null; then
    fail "make dev thoát sớm"
  fi
  if api_ok && web_ok; then
    break
  fi
  sleep 1
  elapsed=$((elapsed + 1))
done

api_ok || fail "FastAPI không trả lời $API_URL/health trong ${TIMEOUT_S}s"
web_ok || fail "Next.js không trả lời $WEB_URL trong ${TIMEOUT_S}s"
echo "dev: API và web cùng lên sau ${elapsed}s"

if [ -n "${LESSON_ID:-}" ]; then
  body=$(curl -sf "$API_URL/lessons/$LESSON_ID") || fail "GET /lessons/$LESSON_ID không trả 2xx"
  case "$body" in
    *'"status":"ready"'*) echo "dev: lesson $LESSON_ID status ready" ;;
    *) fail "lesson $LESSON_ID không ở trạng thái ready" ;;
  esac
fi

stop_job

# Cổng phải được giải phóng (chờ tối đa 15 s cho worker tắt hẳn).
waited=0
while [ "$waited" -lt 15 ]; do
  if [ -z "$(listening 8000)" ] && [ -z "$(listening 3000)" ]; then
    break
  fi
  sleep 1
  waited=$((waited + 1))
done
for port in 8000 3000; do
  if [ -n "$(listening "$port")" ]; then
    fail "cổng $port vẫn mở sau khi dừng make dev"
  fi
done

rm -f "$LOG"
echo "DEV-SMOKE OK"
exit 0
