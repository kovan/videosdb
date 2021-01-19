certbot certonly --dns-google --dns-google-credentials ~/creds.json -d "*.enlightenment.yoga" -d enlightenment.yoga -i nginx  --server https://acme-v02.api.letsencrypt.org/directory
