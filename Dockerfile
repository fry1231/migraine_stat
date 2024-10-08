FROM python:3.10.11-slim

WORKDIR /migrebot

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY src/requirements.txt .

RUN <<EOF /bin/sh
    apt-get update
    apt-get install -y wget gnupg2 lsb-release
    sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/postgres.list'
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
    apt-get update
    apt-get -y install postgresql-client-15
    rm -rf /var/lib/apt/lists/*
EOF

RUN pip install -r requirements.txt

COPY . .