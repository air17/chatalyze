# syntax=docker/dockerfile:1
FROM python:3.9
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY chatalyze /code/
WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt
