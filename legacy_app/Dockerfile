FROM python:3.11

RUN apt-get update
RUN apt-get install -y libgl-dev libmagic-dev

RUN mkdir /app
WORKDIR /app

COPY ./legacy_app/ /app
COPY ./redbox/ /app/redbox
COPY ./setup.py /app

RUN pip install -r requirements.txt

EXPOSE 8501

ENTRYPOINT [ "streamlit", "run", "--server.address", "0.0.0.0", "--server.port", "8501", "app/Welcome.py" ]
