FROM debian:bookworm-slim
RUN echo 'root:toor' | chpasswd
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt update
RUN apt install -y curl
RUN apt clean


WORKDIR /app

RUN curl -fsSL https://install.julialang.org | sh

ADD poetry.lock pyproject.toml  /app/

ENV PATH="/root/.local/bin:${PATH}"
RUN echo $PATH
RUN poetry install --no-interaction


COPY  . .




ENTRYPOINT ["poetry"]

