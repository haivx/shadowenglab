# ShadowEngLab: lệnh phát triển (FND-05).
# Viết cho GNU Make 3.81 của macOS (/usr/bin/make): không dùng -O, .ONESHELL hay $(file).
# Recipe là POSIX sh. Không đặt trap gửi tín hiệu cho cả process group trong recipe (Pitfall 13).

URL ?= $(shell cat scripts/smoke_video.url 2>/dev/null)
START ?=
END ?=
BUDGET ?=
# Bản GSD mà .planning/ được viết cho; `make gsd` cài lại đúng bản này vào .claude/ (không commit).
GSD_VERSION ?= 1.16.0

.PHONY: setup dev dev-api dev-web dev-eval test lint eval eval-tag smoke smoke-jobs smoke-score contracts contracts-check gsd relpaths

# Kiểm tra system dependency (chỉ hướng dẫn, D-25), cài từ lockfile đã duyệt, tải/kiểm tra model.
setup:
	@sh scripts/check_deps.sh
	pnpm install --frozen-lockfile
	uv sync --project services/audio --frozen
	uv run --project services/audio --frozen python -m audio_service.setup_models

# FastAPI (127.0.0.1:8000) và Next.js (localhost:3000) chạy song song.
dev:
	@$(MAKE) -j2 dev-api dev-web

# Chỉ lắng nghe localhost (T-01-20).
dev-api:
	cd services/audio && uv run --frozen uvicorn audio_service.main:app --reload --host 127.0.0.1 --port 8000

dev-web:
	pnpm --filter @shadowenglab/web dev

dev-eval:
	pnpm --filter @shadowenglab/eval dev

# Drift gate D-20 chạy trước, rồi vitest và pytest.
test: contracts-check
	pnpm -r --if-present test
	cd services/audio && uv run --frozen pytest

# Một cách gọi duy nhất: ruff chạy từ services/audio để đọc [tool.ruff] của project.
lint:
	pnpm exec eslint .
	pnpm exec prettier --check .
	pnpm --filter @shadowenglab/contracts exec tsc --noEmit -p tsconfig.json
	cd services/audio && uv run --frozen ruff check --config pyproject.toml . ../../scripts ../../eval
	cd services/audio && uv run --frozen ruff format --check --config pyproject.toml . ../../scripts ../../eval

# Chấm lại bộ eval tuning bằng scorer hiện tại → eval/report.md (D-06, D-16; chỉ đọc DATA_DIR).
eval:
	uv run --project services/audio --frozen python eval/analyze.py

# Ghép clip đã lưu bằng "Lưu clip cho eval" với case đã viết trước (Phase 4, D-01); hỏi từng clip. Các lệnh khác: eval/tag_clips.py words|add|split|check.
eval-tag:
	uv run --project services/audio --frozen python eval/tag_clips.py tag

# Chạy pipeline tạo bài trên video smoke (hoặc URL=...). START/END/BUDGET là tuỳ chọn.
smoke:
	uv run --project services/audio --frozen python scripts/smoke_lesson.py "$(URL)" $(if $(START),--start $(START)) $(if $(END),--end $(END)) $(if $(BUDGET),--budget-s $(BUDGET))

# Hai bài tạo liên tiếp qua API thật trên DATA_DIR tạm, không OPENAI_API_KEY (Phase 2, tiêu chí 2 và 4).
smoke-jobs:
	uv run --project services/audio --frozen python scripts/smoke_jobs.py "$(URL)"

# Chấm tự so + chéo câu + thời gian trên một bài thật (Phase 3, chỉ đọc DATA_DIR). LESSON= là tuỳ chọn.
smoke-score:
	uv run --project services/audio --frozen python scripts/smoke_score.py $(if $(LESSON),--lesson $(LESSON))

contracts:
	sh scripts/contracts_gen.sh

contracts-check:
	sh scripts/contracts_check.sh

# Cài lại bộ GSD (agents, commands, workflows, hooks) vào .claude/ sau khi clone. .claude/ chỉ commit CLAUDE.md.
gsd:
	npx -y @opengsd/gsd-core@$(GSD_VERSION) --claude --local

# Đổi đường dẫn tuyệt đối của máy local trong .planning/ thành đường dẫn tương đối. Chạy trước khi push.
relpaths:
	sh scripts/relativize_paths.sh
