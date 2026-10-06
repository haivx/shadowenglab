# ShadowEngLab: lệnh phát triển (FND-05).
# Viết cho GNU Make 3.81 của macOS (/usr/bin/make): không dùng -O, .ONESHELL hay $(file).
# Recipe là POSIX sh. Không đặt trap gửi tín hiệu cho cả process group trong recipe (Pitfall 13).

URL ?= $(shell cat scripts/smoke_video.url 2>/dev/null)
START ?=
END ?=
BUDGET ?=

.PHONY: setup dev dev-api dev-web dev-eval test lint eval smoke contracts contracts-check

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
	cd services/audio && uv run --frozen ruff check --config pyproject.toml . ../../scripts
	cd services/audio && uv run --frozen ruff format --check --config pyproject.toml . ../../scripts

# Stub: Phase 4 (EVL-02) hiện thực eval/analyze.py.
eval:
	@echo "make eval: stub — Phase 4 (EVL-02) sẽ chạy eval/analyze.py → eval/report.md"

# Chạy pipeline tạo bài trên video smoke (hoặc URL=...). START/END/BUDGET là tuỳ chọn.
smoke:
	uv run --project services/audio --frozen python scripts/smoke_lesson.py "$(URL)" $(if $(START),--start $(START)) $(if $(END),--end $(END)) $(if $(BUDGET),--budget-s $(BUDGET))

contracts:
	sh scripts/contracts_gen.sh

contracts-check:
	sh scripts/contracts_check.sh
