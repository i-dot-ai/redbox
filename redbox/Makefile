.PHONY: app reqs

-include .env
export


reqs:
	poetry install


app:
	poetry run streamlit run legacy_app/Welcome.py --server.port 8501

run:
	docker compose up -d elasticsearch kibana app embed minio miniocreatebuckets

stop:
	docker compose down

clean:
	docker compose down -v --rmi all --remove-orphans

build:
	docker compose build

rebuild:
	docker compose build --no-cache

test:
	poetry run --directory redbox pytest redbox/tests --cov=redbox -v --cov-report=term-missing --cov-fail-under=40
	poetry run --directory app/workers/embed  pytest app/workers/embed --cov=app -v --cov-report=term-missing --cov-fail-under=65

lint:
	poetry run ruff check .

format:
	poetry run ruff format .
	# additionally we format, but not lint, the notebooks
	poetry run ruff format **/*.ipynb

checktypes:
	poetry run mypy redbox app tests --ignore-missing-imports
	poetry run mypy legacy_app --follow-imports skip --ignore-missing-imports
