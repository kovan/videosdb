FROM gcr.io/cloud-builders/docker
RUN sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin
ENTRYPOINT [ "/usr/local/bin/task" ]
