.PHONY: up down logs ps build test
up:
	docker compose up --build
down:
	docker compose down
logs:
	docker compose logs -f --tail=100
ps:
	docker compose ps
build:
	docker compose build
test:
	docker compose --profile test up -d --wait test-db
	docker compose --profile test run --rm --no-deps \
		-e RATE_LIMIT_ENABLED=false \
		-e REDIS_URL= \
		-e DATABASE_URL=postgresql+psycopg://takeaway_test:test_only_password@test-db:5432/takeaway_test \
		api sh -c "python tests/setup_test_db.py && pytest -q"
