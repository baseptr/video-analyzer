.PHONY: dev prod migrate test clean

# Development
dev:
	docker-compose up --build

# Production (detached)
prod:
	docker-compose up -d --build

# Stop all containers
stop:
	docker-compose down

# Run database migrations
migrate:
	docker-compose exec api alembic upgrade head

# Create new migration
migration:
	docker-compose exec api alembic revision --autogenerate -m "$(MSG)"

# Run tests
test:
	docker-compose exec api pytest tests/ -v

# Seed benchmark data
seed:
	docker-compose exec api python scripts/seed_benchmarks.py

# View logs
logs:
	docker-compose logs -f api

# Clean up
clean:
	docker-compose down -v
	docker system prune -f

# Local development (without Docker)
local-dev:
	uvicorn api.main:app --reload --port 8000

# Install dependencies locally
install:
	pip install -r requirements.txt
