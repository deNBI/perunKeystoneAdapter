FROM python:3.6-alpine

RUN apk --no-cache add musl-dev gcc linux-headers libffi-dev openssl-dev

RUN mkdir -p /pka/

COPY requirements /requirements

RUN pip install -r /requirements/default.txt

COPY README.md setup.py MANIFEST.in /pka/
COPY requirements /pka/requirements
COPY denbi /pka/denbi

RUN cd /pka/ && \
    python setup.py install

