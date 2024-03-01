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

test:
	poetry run pytest tests --ignore django_app --cov=redbox -v --cov-report=term-missing --cov-fail-under=35

test-django:
	docker-compose up -d db
	docker-compose run --env ENVIRONMENT="TEST" --env PYTHONPATH=/app/django_app/ django-app poetry run pytest /app/django_app/tests/ --ds redbox_app.settings -v --cov=redbox_app.redbox_core --cov-fail-under 10

lint:
	poetry run ruff check .

format:
	poetry run ruff format .
	# additionally we format, but not lint, the notebooks
	# poetry run ruff format **/*.ipynb

checktypes:
	poetry run mypy redbox app tests --ignore-missing-imports
	# poetry run mypy legacy_app --follow-imports skip --ignore-missing-imports

check-migrations:
	docker-compose build django-app
	docker-compose run --env ENVIRONMENT="TEST" django-app poetry run python /app/django_app/manage.py migrate
	docker-compose run --env ENVIRONMENT="TEST" django-app poetry run python /app/django_app/manage.py makemigrations --check

check-python-code:
	poetry run ruff check .
	poetry run bandit -ll -r ./redbox
	poetry run bandit -ll -r ./django_app
	poetry run mypy ./redbox --ignore-missing-imports
	poetry run mypy ./django_app --ignore-missing-imports

reset-db:
	docker-compose down db --volumes
	docker-compose up -d db