FROM python:3.6-alpine

RUN apk --no-cache add gcc musl-dev linux-headers

RUN mkdir -p /pka/

COPY README.md setup.py requirements.txt /pka/
COPY denbi /pka/denbi/
COPY test /pka/denbi/

RUN cd /pka/ && \
    python setup.py install

RUN apk --no-cache add libffi-dev openssl-dev
RUN pip install gunicorn python-openstackclient

ENTRYPOINT ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:5000", "denbi.scripts.perun_propagation_service:app"]

EXPOSE 5000
