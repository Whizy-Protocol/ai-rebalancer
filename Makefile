.PHONY: lint lint-fix format check test

lint:
	@echo "Running Ruff linter..."
	ruff check .

lint-fix:
	@echo "Auto-fixing linting issues..."
	ruff check . --fix

format:
	@echo "Formatting code with Ruff..."
	ruff format .

check: lint format

test:
	@echo "Running tests..."
	pytest test/ -v -m "not integration"

test-integration:
	@echo "Running integration tests with real API..."
	pytest test/test_integration.py -v -m integration

test-all:
	@echo "Running all tests..."
	pytest test/ -v

test-coverage:
	@echo "Running tests with coverage..."
	pytest test/ -v -m "not integration" --cov=src --cov-report=term-missing

clean:
	@echo "Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
