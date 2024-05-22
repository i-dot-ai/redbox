from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from core_api.src.routes.chat import chat_app
from core_api.src.routes.file import file_app
from redbox.models import Settings, StatusResponse

# === Logging ===

env = Settings()


# === API Setup ===

start_time = datetime.now(tz=UTC)


# Create API

app = FastAPI(
    title="Core API",
    description="Redbox Core API",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Health check"},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# === API Routes ===

# Basic Setup


@app.get("/", include_in_schema=False, response_class=RedirectResponse)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["health"])
def health() -> StatusResponse:
    """Returns the health of the API

    Returns:
        StatusResponse: The health of the API
    """

    uptime = datetime.now(UTC) - start_time
    uptime_seconds = uptime.total_seconds()

    output = StatusResponse(
        status="ready",
        uptime_seconds=uptime_seconds,
        version=app.version,
    )

    return output


app.mount("/chat", chat_app)
app.mount("/file", file_app)
