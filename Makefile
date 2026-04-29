.PHONY: frontend-dev backend-dev backend-test backend-lint

# === Frontend ===
frontend-dev:
	cd frontend && npm run dev

# === Backend ===
backend-dev:
	cd backend && uvicorn app.main:app --reload --port 8000

backend-test:
	cd backend && python -m pytest

backend-lint:
	cd backend && ruff check .
