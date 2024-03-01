.PHONY: app reqs

-include .env
export


reqs:
	poetry install


app:
	poetry run streamlit run legacy_app/Welcome.py --server.port 8501

run:
	docker compose up -d elasticsearch kibana app embed minio miniocreatebuckets rabbitmq core-api

stop:
	docker compose down

clean:
	docker compose down -v --rmi all --remove-orphans

build:
	docker compose build

rebuild:
	docker compose build --no-cache

testembed:
	poetry install --no-root --no-ansi --with worker,embed,api,dev --without ai,ingest
	poetry run pytest embed/tests --cov=embed/src -v --cov-report=term-missing --cov-fail-under=45

testredbox:
	poetry install --no-root --no-ansi --with worker,api,dev --without embed,ai,streamlit-app,ingest
	poetry run pytest redbox/tests --cov=redbox -v --cov-report=term-missing --cov-fail-under=45

lint:
	poetry run ruff check .

format:
	poetry run ruff format .
	# additionally we format, but not lint, the notebooks
	# poetry run ruff format **/*.ipynb

checktypes:
	poetry run mypy redbox embed ingest --ignore-missing-imports
	# poetry run mypy legacy_app --follow-imports skip --ignore-missing-imports
