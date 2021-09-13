FROM python:bullseye
RUN echo 'root:toor' | chpasswd
RUN apt update
RUN apt install -y certbot anacron nginx sudo
RUN apt clean


COPY frontend.nginx /etc/nginx/sites-enabled
COPY ipfs.nginx /etc/nginx/sites-enabled

CMD ["nginx", "-g", "daemon off;"]