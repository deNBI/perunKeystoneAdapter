FROM python:3.9-alpine

RUN apk add --no-cache build-base musl-dev gcc linux-headers libffi-dev openssl-dev

RUN mkdir -p /perun/upload
RUN mkdir -p /perun/log

COPY requirements /requirements

RUN pip install -r /requirements/default.txt

COPY README.md setup.py MANIFEST.in /
COPY denbi /denbi

EXPOSE 5000/tcp

WORKDIR /
CMD ["gunicorn", "--workers", "1", "--bind","0.0.0.0:5000", "denbi.scripts.perun_propagation_service:app"]