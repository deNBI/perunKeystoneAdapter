FROM python:3.10-alpine

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

# example call
# docker run -d --env-list <ENVIRONMENT_FILE> -v /var/log/pka:/var/log/pka denbi/pka
# where ENVIRONMENT_FILE should contain valid openstack credentials ...

# OS_REGION_NAME=RegionOne
# OS_PROJECT_DOMAIN_ID=default
# OS_INTERFACE=public
# OS_AUTH_URL=http://192.168.20.55/identity
# OS_USERNAME=admin
# OS_PROJECT_ID=d3c8f94c182a4ce1b9122e9abfe544bb
# OS_USER_DOMAIN_NAME=Default
# OS_PROJECT_NAME=admin
# OS_PASSWORD=secret
# OS_IDENTITY_API_VERSION=3

# and additions options for the perun keystone adapter
# PKA_BASE_DIR=
# PKA_KEYSTONE_READ_ONLY=False
# PKA_TARGET_DOMAIN_NAME=elixir
# PKA_DEFAULT_ROLE=
# PKA_DEFAULT_NESTED=False
# PKA_ELIXIR_NAME=False
# PKA_SUPPORT_QUOTA=False
# PKA_SUPPORT_ROUTER=False
# PKA_SUPPORT_NETWORK=False
# PKA_EXTERNAL_NETWORK_ID=
# PKA_SUPPORT_DEFAULT_SSH_SGRULE=
