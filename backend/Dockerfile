FROM debian:bookworm-slim
RUN echo 'root:toor' | chpasswd
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt update
RUN apt install -y python3-minimal
RUN apt install -y python3-distutils
RUN apt install -y curl
RUN apt install -y python3-poetry
RUN apt clean

WORKDIR /app

#RUN curl -sSL https://install.python-poetry.org | python3 -


ADD poetry.lock pyproject.toml  /app/

ENV PATH="/root/.local/bin:${PATH}"
RUN echo $PATH
RUN poetry install --no-interaction


COPY  . .




ENTRYPOINT ["poetry"]

