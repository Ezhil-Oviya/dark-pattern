.PHONY: init backend frontend ai docker-up docker-down test lint

init:
	python -m venv backend/.venv
	cd backend && .venv/Scripts/pip install -r requirements.txt
	cd frontend && npm install
	cd ai && python -m venv .venv && .venv/Scripts/pip install -r requirements-ai.txt

backend:
	cd backend && .venv/Scripts/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

ai:
	cd ai && .venv/Scripts/python -m pytest

docker-up:
	docker compose up --build

docker-down:
	docker compose down

test:
	cd backend && .venv/Scripts/pytest
	cd frontend && npm test -- --run

lint:
	cd frontend && npm run lint
