test:
	export $(grep -v '^#' ../.env.test | xargs) && COMPRESSION_ENABLED=False && POSTGRES_HOST=localhost && CORE_API_HOST=testserver && DEBUG=True && poetry run pytest tests/ --ds redbox_app.settings
