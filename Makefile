.PHONY: help setup sample demo api web test lint format clean

# --- Default ---
help:
	@echo "Essay Integrity Checker — common commands"
	@echo ""
	@echo "  make setup    Tạo venv + install dependencies"
	@echo "  make sample   Generate sample essays + gold dataset"
	@echo "  make demo     Run CLI demo trên 1 PDF mẫu"
	@echo "  make api      Run FastAPI backend (uvicorn --reload)"
	@echo "  make web      Run Vite dev server (frontend)"
	@echo "  make test     Run pytest"
	@echo "  make lint     Run ruff + black check"
	@echo "  make format   Auto-format code"
	@echo "  make clean    Remove caches + generated data"

# --- Setup ---
setup:
	python -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements-dev.txt
	cp -n .env.example .env || true
	cp -n configs/config.example.yaml configs/config.yaml || true

# --- Sample data ---
sample:
	. .venv/bin/activate && python scripts/gen_sample_essays.py
	. .venv/bin/activate && python scripts/gen_gold_dataset.py

# --- Demo ---
demo:
	. .venv/bin/activate && python -m integrity_checker.pipeline.integrity_pipeline \
	    data/essays/essay_02_mixed.pdf --output report.json

# --- Services ---
api:
	. .venv/bin/activate && uvicorn integrity_checker.api.main:app --reload --port 8000

web:
	cd web && npm install && npm run dev

# --- Tests ---
test:
	. .venv/bin/activate && pytest tests/ -v

test-unit:
	. .venv/bin/activate && pytest tests/unit/ -v

test-integration:
	. .venv/bin/activate && pytest tests/integration/ -v -m integration

# --- Lint ---
lint:
	. .venv/bin/activate && ruff check src/ tests/
	. .venv/bin/activate && black --check src/ tests/

format:
	. .venv/bin/activate && ruff check --fix src/ tests/
	. .venv/bin/activate && black src/ tests/
	. .venv/bin/activate && isort src/ tests/

# --- Cleanup ---
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	rm -f data/app.db data/app.*.db
	rm -rf data/cache/*.json data/cache/*.sqlite
