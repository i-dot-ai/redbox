.PHONY: app reqs

-include .env
export


reqs:
	poetry install

run:
	docker compose up -d elasticsearch kibana embedder ingester minio miniocreatebuckets redis core-api db django-app

stop:
	docker compose down

clean:
	docker compose down -v --rmi all --remove-orphans

build:
	docker compose build

rebuild:
	docker compose build --no-cache

test-core-api:
	poetry install --no-root --no-ansi --with worker,api,dev --without ai,ingester
	poetry run pytest core_api/tests --cov=core_api/src -v --cov-report=term-missing --cov-fail-under=45

test-embedder:
	poetry install --no-root --no-ansi --with worker,api,dev --without ai,ingester
	poetry run pytest embedder/tests --cov=embedder/src -v --cov-report=term-missing --cov-fail-under=50

test-redbox:
	poetry install --no-root --no-ansi --with worker,api,dev --without ai,streamlit-app,ingester
	poetry run pytest redbox/tests --cov=redbox -v --cov-report=term-missing --cov-fail-under=45

test-ingester:
	poetry install --no-root --no-ansi --with worker,ingester,dev --without ai,streamlit-app,api
	poetry run pytest ingester/tests --cov=ingester -v --cov-report=term-missing --cov-fail-under=40

test-django:
	docker compose up -d --wait db
	docker compose run django-app poetry run pytest django_app/tests/ --ds redbox_app.settings -v --cov=redbox_app.redbox_core --cov-fail-under 10

test-integration:
	docker compose down
	cp .env.example .env
	docker compose build core-api embedder ingester
	docker compose up -d core-api embedder ingester
	poetry install --no-root --no-ansi --with dev --without ai,streamlit-app,api,worker,ingester
	sleep 10
	poetry run pytest tests

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
	poetry run mypy redbox embedder ingester --ignore-missing-imports
	# poetry run mypy legacy_app --follow-imports skip --ignore-missing-imports

check-migrations:
	docker compose build django-app
	docker compose run django-app poetry run python django_app/manage.py migrate
	docker compose run django-app poetry run python django_app/manage.py makemigrations --check

reset-db:
	docker compose down db --volumes
	docker compose up -d db
