build:
	poetry install --no-root

test:
	poetry run pytest . --cov=. -v --cov-report=term-missing --cov-fail-under=65

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

checktypes:
	poetry run mypy . --ignore-missing-imports
