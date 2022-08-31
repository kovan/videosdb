
FROM mwalbeck/python-poetry
RUN echo 'root:toor' | chpasswd
SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt update
RUN apt install -y git
WORKDIR /root
ADD poetry.lock pyproject.toml  ./
RUN poetry install --no-dev
COPY  . .



ENTRYPOINT ["poetry", "run", "python", "-O", "-m", "videosdb"]

