FROM python:3.6-alpine

RUN apk --no-cache add gcc musl-dev linux-headers libffi-dev openssl-dev

RUN mkdir -p /pka/

COPY README.md setup.py requirements.txt /pka/
COPY denbi /pka/denbi/
COPY test /pka/denbi/

RUN cd /pka/ && \
    python setup.py install && \
    pip install gunicorn python-openstackclient

RUN echo "gunicorn --workers 1 --bind \${BIND_HOST:-0.0.0.0}:\${BIND_PORT:-5000} denbi.scripts.perun_propagation_service:app" > /run.sh && \
    chmod +x /run.sh

ENTRYPOINT ["sh", "/run.sh"]

EXPOSE 5000
