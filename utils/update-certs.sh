DST=/var/lib/docker/volumes/global-nginx-proxy_dhparam/_data
certbot renew
cp /etc/letsencrypt/live/ipfs.spiritualityresources.net/privkey.pem $DST/privkey.pem
cp /etc/letsencrypt/live/ipfs.spiritualityresources.net/fullchain.pem $DST/fullchain.pem
cp /etc/letsencrypt/live/resources.spiritualityresources.net/privkey.pem $DST/privkey-res.pem
cp /etc/letsencrypt/live/resources.spiritualityresources.net/fullchain.pem $DST/fullchain-res.pem
