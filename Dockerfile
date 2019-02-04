FROM python:3.6-alpine

RUN apk --no-cache add musl-dev gcc linux-headers libffi-dev openssl-dev

RUN mkdir -p /pka/

COPY README.md setup.py MANIFEST.in /pka/
COPY denbi /pka/denbi/
COPY requirements /pka/requirements/

RUN cd /pka/ && \
    python setup.py install && \
    pip install gunicorn python-openstackclient

EXPOSE 5000
