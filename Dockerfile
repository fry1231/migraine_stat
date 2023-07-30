FROM python:3.10.11-slim-bullseye

WORKDIR /migrebot

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY src/requirements.txt .
RUN pip install -r requirements.txt

COPY . .