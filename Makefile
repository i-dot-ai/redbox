.PHONY: app reqs venv

-include .env
export

PYTHON = python3


reqs:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -r requirements.dev.txt

venv:
	$(PYTHON) -m venv .venv && \
	source .venv/bin/activate && \
	make reqs
	@echo "========================"
	@echo "Virtual environment successfully created. To activate the venv:"
	@echo "	\033[0;32msource .venv/bin/activate"

app:
	streamlit run app/Welcome.py --server.port 8501

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
	$(PYTHON) -m pytest -v --cov=app --cov-report=term-missing --cov-fail-under=100 --cov-config=.coveragerc

lint:
	$(PYTHON) -m pylint app

format:
	$(PYTHON) -m isort --profile black .
	$(PYTHON) -m black .
