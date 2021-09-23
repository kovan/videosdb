FROM python:bullseye
COPY ipfs /usr/local/bin


# these not needed because we already have the repo configured:
#COPY ipfs.config /etc/ipfs.config.default
#RUN ipfs init --profile lowpower
#RUN ipfs config --json Experimental.FilestoreEnabled true
#RUN echo "this is a test" > test.txt
#RUN ipfs add test.txt
ENV IPFS_PATH /mnt/ipfs-repo
CMD ["nice", "-n", "10", "/usr/local/bin/ipfs", "daemon"]