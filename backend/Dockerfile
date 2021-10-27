
FROM python:3.9-bullseye
RUN echo 'root:toor' | chpasswd
SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt update
RUN apt install -y python3-virtualenv

RUN apt clean

RUN pip install certifi
COPY utils/install_certificates.py /tmp
RUN python /tmp/install_certificates.py


RUN useradd -m appuser
WORKDIR /app
RUN chown appuser:appuser .
USER appuser

RUN wget  http://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py -O - | python3
ENV PATH="/home/appuser/.poetry/bin:${PATH}"


#RUN mkdir /app/.cache && chown appuser:appuser /app/.cache
#RUN mkdir /app/logs && chown appuser:appuser /app/logs

#VOLUME /app/.cache
#VOLUME /app/logs
ADD --chown=appuser:appuser poetry.lock pyproject.toml  /app/
RUN poetry install --no-dev
COPY --chown=appuser:appuser . .

EXPOSE $PORT


CMD ["/bin/bash", "-c",  "poetry run gunicorn --bind 0.0.0.0:$PORT --threads=3  --timeout 300 --log-level=info --log-file=- project.wsgi"]
#CMD ["/app/utils/entrypoint.sh"]
