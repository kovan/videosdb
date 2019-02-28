DOMAIN=enlightenment.yoga
SRC=/etc/letsencrypt/live/$DOMAIN
DST=/var/lib/docker/volumes/global-nginx-proxy_certs/_data

certbot renew --quiet
cp $SRC/fullchain.pem $DST/$DOMAIN.fullchain.pem
cp $SRC/privkey.pem $DST/$DOMAIN.privkey.pem
