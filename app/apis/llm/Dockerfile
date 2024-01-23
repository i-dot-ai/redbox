FROM python:3.11

COPY requirements.txt /tmp/pip-tmp/
RUN pip install --requirement /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-

COPY app.py /app.py

EXPOSE 5001

# Run FastAPI

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001"]