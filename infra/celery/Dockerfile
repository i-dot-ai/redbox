FROM python:3.11

ADD requirements.txt /tmp/pip-tmp/
RUN pip install --requirement /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-

RUN mkdir /celery_home/
ADD app/ /celery_home/app/
WORKDIR /celery_home/

# Run Celery
CMD ["celery",  "-A", "app", "worker", "-l", "INFO"]