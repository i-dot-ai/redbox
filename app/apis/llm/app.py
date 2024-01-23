from datetime import datetime
from typing import List

import pydantic
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

# === Data Models ===


class StatusResponse(pydantic.BaseModel):
    status: str
    uptime_seconds: float
    version: str


# === API Setup ===

start_time = datetime.now()
IS_READY = False


# Create API

app = FastAPI(
    title="Ingest API",
    description="An API for ingesting data into the system",
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


@app.get("/health", response_model=StatusResponse, tags=["health"])
def health():
    """Returns the health of the API

    Returns:
        StatusResponse: The health of the API
    """

    uptime = datetime.now() - start_time
    uptime_seconds = uptime.total_seconds()

    output = {"status": None, "uptime_seconds": uptime_seconds, "version": app.version}

    if IS_READY:
        output["status"] = "ready"
    else:
        output["status"] = "loading"

    return output
