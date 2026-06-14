.PHONY: dev up down test migrate lint

dev:
	docker compose -f docker-compose.yml up --build

up:
	docker compose up -d

down:
	docker compose down

test:
	cd backend && python -m pytest tests/ -v

migrate:
	cd backend && alembic upgrade head

lint:
	cd backend && python -m ruff check app/
	cd frontend && npm run lint
