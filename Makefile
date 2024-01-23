.PHONY: app reqs venv

-include .env
export

PYTHON = python3

setup-elastic:
	docker compose up setup

run:
	docker compose up -d elasticsearch kibana app embed minio miniocreatebuckets rabbitmq

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
