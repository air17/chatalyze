# syntax=docker/dockerfile:1
FROM python:3.10
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY chatalyze /code/
WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends gettext \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
