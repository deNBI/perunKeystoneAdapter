FROM python:3.9-alpine

RUN apk add --no-cache build-base musl-dev gcc linux-headers libffi-dev openssl-dev

RUN mkdir -p /pka/

COPY requirements /pka/requirements

RUN pip install -r /pka/requirements/default.txt

COPY README.md setup.py MANIFEST.in /pka/
COPY denbi /pka/denbi

RUN cd /pka/ && \
    python setup.py install