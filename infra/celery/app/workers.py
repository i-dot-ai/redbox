import logging
import time

import lorem

from .celery import app


@app.task
def ingest(file):
    logging.info(f"Starting ingest process for {file}")

    # write file to S3 and hand identifier to .parse
    file_url = f"fake://url.for/{file}"

    parse.delay(file_url)

    return f"{file_url} ingest started"


@app.task
def parse(file_url):
    logging.info(f"Starting parse process for {file_url}")

    # pretend we've got the file from S3
    # and we chunk it up
    chunks = [lorem.sentence() for _n in range(10)]
    for chunk in chunks:
        embed.delay(chunk, file_url)

    return f"{file_url} parse completed, chunks enqueued"


@app.task
def embed(chunk, file_url):
    logging.info(f"Starting chunk embedding for a chunk from file {file_url}")

    logging.info(f"embedding of {file_url} completed")

    return f"Chunked {chunk} from file {file_url}"
