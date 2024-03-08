.PHONY: app reqs

-include .env
export


reqs:
	poetry install


app:
	poetry run streamlit run legacy_app/Welcome.py --server.port 8501

run:
	docker compose up -d elasticsearch kibana app embed minio miniocreatebuckets rabbitmq core-api db django-app

stop:
	docker compose down

clean:
	docker compose down -v --rmi all --remove-orphans

build:
	docker compose build

rebuild:
	docker compose build --no-cache

test-embed:
	poetry install --no-root --no-ansi --with worker,embed,api,dev --without ai,ingest,django-app,pytest-django
	poetry run pytest embed/tests --cov=embed/src -v --cov-report=term-missing --cov-fail-under=45

test-redbox:
	poetry install --no-root --no-ansi --with worker,api,dev --without embed,ai,streamlit-app,ingest,django-app,pytest-django
	poetry run pytest redbox/tests --cov=redbox -v --cov-report=term-missing --cov-fail-under=45

test-ingest:
	poetry install --no-root --no-ansi --with worker,ingest,dev --without embed,ai,streamlit-app,api,django-app,pytest-django
	poetry run pytest ingest/tests --cov=ingest -v --cov-report=term-missing --cov-fail-under=40

test-django:
	docker-compose up -d db
	docker-compose run django-app poetry run pytest django_app/tests/ --ds redbox_app.settings -v --cov=redbox_app.redbox_core --cov-fail-under 10

lint:
	poetry run ruff check .

format:
	poetry run ruff format .
	# additionally we format, but not lint, the notebooks
	# poetry run ruff format **/*.ipynb

safe:
	poetry run bandit -ll -r ./redbox
	poetry run bandit -ll -r ./django_app
	poetry run mypy ./redbox --ignore-missing-imports
	poetry run mypy ./django_app --ignore-missing-imports

checktypes:
	poetry run mypy redbox embed ingest --ignore-missing-imports
	# poetry run mypy legacy_app --follow-imports skip --ignore-missing-imports

check-migrations:
	docker-compose build django-app
	docker-compose run django-app poetry run python django_app/manage.py migrate
	docker-compose run django-app poetry run python django_app/manage.py makemigrations --check

reset-db:
	docker-compose down db --volumes
	docker-compose up -d db
