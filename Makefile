.PHONY: help install run test lint format docker-up docker-down migrate clean

# Variables
PYTHON := venv/bin/python
PIP := venv/bin/pip
UVICORN := venv/bin/uvicorn
PYTEST := venv/bin/pytest
RUFF := venv/bin/ruff
MYPY := venv/bin/mypy

# Default target
help:
	@echo "Available commands:"
	@echo "  make install    - Install project dependencies"
	@echo "  make run        - Run the FastAPI development server"
	@echo "  make test       - Run the test suite with pytest"
	@echo "  make lint       - Run ruff and mypy for code quality checks"
	@echo "  make format     - Format code using ruff"
	@echo "  make docker-up  - Start PostgreSQL and Redis via Docker Compose"
	@echo "  make docker-down- Stop Docker Compose services"
	@echo "  make migrate    - Run Alembic database migrations"
	@echo "  make clean      - Remove Python cache and build artifacts"

# Install dependencies
install:
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]

# Run the development server
run:
	$(UVICORN) app.main:app --host 127.0.0.1 --port 8000 --reload

# Run tests
test:
	$(PYTEST) tests/ -v --tb=short

# Run linters and type checkers
lint:
	$(RUFF) check app tests
	$(MYPY) app tests

# Format code
format:
	$(RUFF) format app tests
	$(RUFF) check --fix app tests

# Start Docker services (Postgres, Redis)
docker-up:
	docker compose up -d postgres redis

# Stop Docker services
docker-down:
	docker compose down

# Run database migrations
migrate:
	$(PYTHON) -m alembic upgrade head

# Clean up cache and build artifacts
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache/
	rm -rf build/
	rm -rf dist/
