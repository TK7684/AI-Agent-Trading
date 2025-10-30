.PHONY: help install test lint format clean build docker-build docker-run

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install all dependencies"
	@echo "  test         - Run all tests"
	@echo "  lint         - Run all linters"
	@echo "  format       - Format all code"
	@echo "  clean        - Clean build artifacts"
	@echo "  build        - Build all components"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container"
	@echo "  security     - Run security scans"

# Install dependencies
install:
	poetry install
	cargo build

# Run tests
test:
	poetry run pytest --cov
	cargo test --workspace

# Run linters
lint:
	poetry run ruff check .
	poetry run mypy .
	cargo clippy --all-targets --all-features -- -D warnings

# Format code
format:
	poetry run ruff format .
	cargo fmt --all

# Security scans
security:
	poetry run bandit -r apps libs
	poetry run safety check
	cargo audit

# Clean build artifacts
clean:
	rm -rf target/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf dist/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build all components
build:
	poetry build
	cargo build --release

# Docker targets
docker-build:
	docker build -t autonomous-trading-system:latest .

docker-run:
	docker run -p 8000:8000 autonomous-trading-system:latest

# Development setup
dev-setup:
	poetry install
	poetry run pre-commit install
	cargo build