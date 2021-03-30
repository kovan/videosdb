# For more information, please refer to https://aka.ms/vscode-docker-python
#FROM python:3.8-slim-buster
FROM ubuntu:20.04
RUN echo 'root:toor' | chpasswd
SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt update
RUN apt install python3-pip git-core curl gcc libffi-dev libssl-dev python3-dev rustc postgresql-common libpq-dev -y
RUN apt autoremove -y
RUN apt clean

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

RUN pip3 install --upgrade pip
RUN pip3 install poetry

WORKDIR /app

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
RUN useradd -m appuser
RUN chown appuser:appuser .
RUN mkdir /app/.cache && chown appuser:appuser /app/.cache
RUN mkdir /app/logs && chown appuser:appuser /app/logs
USER appuser

# RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
# ENV PATH="$PATH:/home/appuser/.poetry/bin"

VOLUME /app/.cache
VOLUME /app/logs
ADD --chown=appuser:appuser poetry.lock pyproject.toml  /app/
RUN poetry install --no-dev
COPY --chown=appuser:appuser . .


EXPOSE 8000

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
# File wsgi.py was not found in subfolder: 'videosdb'. Please enter the Python path to wsgi file.
CMD ["poetry", "run", "gunicorn", "--preload", "--bind", "0.0.0.0:8000", "project.wsgi"]
