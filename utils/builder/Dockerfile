FROM gcr.io/cloud-builders/docker
RUN curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-405.0.0-linux-x86_64.tar.gz
RUN tar -xf google-cloud-cli-405.0.0-linux-x86_64.tar.gz
RUN ./google-cloud-sdk/install.sh -q
RUN sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin
RUN apt install -y netcat
RUN apt install -y ltrace strace


RUN git config --global --add safe.directory /app
ENV PATH="${PATH}:/google-cloud-sdk/bin"
ENTRYPOINT [ "/usr/local/bin/task" ]
