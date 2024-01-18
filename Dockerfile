FROM python:3.11

RUN apt-get update
RUN apt-get install -y libgl-dev libmagic-dev

RUN mkdir /app
COPY app/ /app/app
COPY requirements.txt /app
COPY redbox/ /app/redbox
COPY setup.py /app
COPY .env /app
COPY download_embedder.py /app
RUN mkdir /app/data
COPY test.py /app
WORKDIR /app

RUN pip install -r requirements.txt
RUN pip install --force-reinstall --no-cache-dir chroma-hnswlib

EXPOSE 8080

ENTRYPOINT [ "streamlit", "run", "--server.address", "0.0.0.0", "--server.port", "8080", "app/Welcome.py" ]
