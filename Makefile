.PHONY: help up down build restart logs ps install run-backend run-frontend test test-backend test-frontend build-frontend clean

help:
	@echo "Available commands:"
	@echo "  make up              Build and start complete Docker stack in background"
	@echo "  make down            Stop and remove containers and networks"
	@echo "  make build           Rebuild Docker images"
	@echo "  make restart         Restart Docker stack"
	@echo "  make logs            Follow container logs"
	@echo "  make ps              List container status"
	@echo "  make install         Install local development dependencies"
	@echo "  make run-backend     Run FastAPI backend locally"
	@echo "  make run-frontend    Run Vite frontend locally"
	@echo "  make test            Run backend and frontend tests"
	@echo "  make test-backend    Run pytest suite"
	@echo "  make test-frontend   Run vitest suite"
	@echo "  make clean           Clean cache files"

up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

restart:
	docker compose restart

logs:
	docker compose logs -f

ps:
	docker compose ps

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

run-backend:
	python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

run-frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	python -m pytest backend/tests -v

test-frontend:
	cd frontend && npm test

build-frontend:
	cd frontend && npm run build

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f backend/*.db backend/*.db-wal backend/*.db-shm app.db app.db-wal app.db-shm 2>/dev/null || true
