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

test:
	docker compose up -d --wait elasticsearch
	docker-compose run test poetry run pytest .
	# --cov=redbox -v --cov-report=term-missing --cov-fail-under=35
	docker-compose up -d db
	docker-compose run --env ENVIRONMENT="TEST" web poetry run pytest tests -v --cov=redbox_core --cov-fail-under 92

lint:
	poetry run ruff check .

format:
	poetry run ruff format .
	# additionally we format, but not lint, the notebooks
	poetry run ruff format **/*.ipynb

checktypes:
	poetry run mypy redbox app tests --ignore-missing-imports
	poetry run mypy legacy_app --follow-imports skip --ignore-missing-imports

check-migrations:
	docker-compose build web
	docker-compose run --env ENVIRONMENT="TEST" web poetry run python manage.py migrate
	docker-compose run --env ENVIRONMENT="TEST" web poetry run python manage.py makemigrations --check

check-python-code:
	chdir app/
	poetry run ruff .
	poetry run bandit -ll -r ./redbox
	poetry run mypy ./ --ignore-missing-imports

reset-db:
	docker-compose down db --volumes
	docker-compose up -d db
