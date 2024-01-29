FROM python:3.11

RUN apt-get update
RUN apt-get install -y libgl-dev libmagic-dev inetutils-ping

RUN mkdir /app
WORKDIR /app

ADD requirements.txt /app
RUN pip install -r requirements.txt

ADD redbox/ /app/redbox
ADD setup.py /app
RUN pip install -e .

ADD download_embedder.py /app
RUN python download_embedder.py

ADD legacy_app /app

EXPOSE 8501

ENTRYPOINT [ "streamlit", "run", "--server.address", "0.0.0.0", "--server.port", "8501", "Welcome.py" ]
