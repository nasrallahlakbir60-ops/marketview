.PHONY: up down logs test test-backend test-frontend migrate seed fetch-news fetch-macro check-feeds prod-up prod-down prod-logs

# --renew-anon-volumes : recrée le volume node_modules du frontend si les dépendances ont changé.
up:
	docker compose up --build --renew-anon-volumes

down:
	docker compose down

logs:
	docker compose logs -f

test: test-backend test-frontend

test-backend:
	docker compose run --rm --no-deps --entrypoint "" backend pytest

test-frontend:
	docker compose run --rm --no-deps frontend npm test

migrate:
	docker compose run --rm backend alembic upgrade head

seed:
	docker compose run --rm backend python -m app.seed

fetch-news:
	docker compose exec backend python -m app.workers.fetch_news

fetch-macro:
	docker compose exec backend python -m app.workers.fetch_macro

check-feeds:
	docker compose exec backend python scripts/check_feeds.py

prod-up:
	docker compose -f docker-compose.prod.yml --env-file .env up -d --build

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f
