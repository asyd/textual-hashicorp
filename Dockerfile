FROM python:3.11.4-slim

RUN pip install poetry

WORKDIR /app
COPY pyproject.toml poetry.lock /app/

RUN poetry install

COPY . /app/

ENTRYPOINT ["/usr/local/bin/poetry", "run"]
