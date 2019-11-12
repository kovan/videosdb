#!env python
import socket
import yaml
import time
import requests
from executor import execute

config = yaml.safe_load(open("config.yaml"))
hostname = config["dns_root"]
published_ip = socket.gethostbyname(hostname)
my_public_ip = requests.get('https://api.ipify.org').text

if published_ip != my_public_ip:
    execute("python manage.py videosdb --update-ip " + my_public_ip)
    print("Updated IP from + " + published_ip + " to " + my_public_ip)
    time.sleep(300)


