.PHONY: setup backend frontend test seed build clean

TEST_ENCRYPTION_KEY=4zrqM1E2z4_bfdxEusZT6X0hgqP-d9qbM9Q1E3L8qjk=

setup:
	python -m venv .venv
	./.venv/bin/python -m pip install -r backend/requirements.txt
	./.venv/bin/python -m playwright install chromium
	cd frontend && npm install --prefer-offline --no-audit --no-fund

backend:
	./.venv/bin/python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev -- --host 0.0.0.0 --port 5173

test:
	ENCRYPTION_KEY=$(TEST_ENCRYPTION_KEY) ./.venv/bin/python -m pytest backend/tests

seed:
	./.venv/bin/python -m backend.scripts.dev_seed

build:
	cd frontend && npm install --prefer-offline --no-audit --no-fund && npm run build

clean:
	rm -rf .venv frontend/node_modules frontend/dist .pytest_cache data
