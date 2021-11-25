FROM python:3.10.0-slim-buster AS er-requester

WORKDIR /requester
COPY requirements/service.txt requirements/service.txt
RUN pip install -r requirements/service.txt

COPY setup.cfg setup.cfg
COPY pyproject.toml pyproject.toml
COPY src/ src/
RUN pip install -e .

COPY key.secret key.secret
