.PHONY: app reqs

-include .env
export


reqs:
	poetry install


app:
	poetry run streamlit run app/Welcome.py --server.port 8501

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
	poetry run pytest -v --cov=app --cov-report=term-missing --cov-fail-under=100 --cov-config=.coveragerc

lint:
	poetry run pylint app

format:
	poetry run isort --profile black .
	poetry run black .
