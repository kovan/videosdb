FROM python:bullseye
COPY ipfs /usr/local/bin

COPY ipfs.config /mnt/ipfs-repo/config

# these not needed because we already have the config:
#RUN ipfs init --profile lowpower
#RUN ipfs config --json Experimental.FilestoreEnabled true
ENV IPFS_PATH /mnt/ipfs-repo
CMD ["nice", "-n", "10", "/usr/local/bin/ipfs", "daemon"]