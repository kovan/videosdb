# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.8-slim-buster
RUN echo 'root:toor' | chpasswd
RUN apt update
RUN apt install git -y

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN python -m pip install poetry 

WORKDIR /app

# Switching to a non-root user, please refer to https://aka.ms/vscode-docker-python-user-rights
RUN useradd -m appuser
RUN chown appuser:appuser .

USER appuser
RUN mkdir /app/.cache && chown appuser:appuser /app/.cache
VOLUME /app/.cacheº
ADD --chown=appuser:appuser poetry.lock pyproject.toml  /app/
RUN poetry install --no-dev
COPY --chown=appuser:appuser . .


EXPOSE 8000

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
# File wsgi.py was not found in subfolder: 'videosdb'. Please enter the Python path to wsgi file.
CMD ["poetry", "run", "gunicorn", "--bind", "0.0.0.0:8000", "project.wsgi"]
