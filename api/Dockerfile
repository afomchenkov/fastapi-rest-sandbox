FROM python:3.11

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY . .

RUN pip install --upgrade pip
RUN python -m ensurepip --upgrade
RUN python -m pip install --upgrade setuptools
RUN pip install --upgrade -r requirements.txt
