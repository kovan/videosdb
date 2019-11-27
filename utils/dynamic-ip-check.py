#!env python
import socket
import yaml
import time
import requests
from executor import execute

def get_public_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

config = yaml.safe_load(open("config.yaml"))
hostname = config["dns_root"]
published_ip = socket.gethostbyname(hostname)
my_public_ip = get_public_ip()
if published_ip != my_public_ip:
    execute("python manage.py videosdb --update-ip " + my_public_ip)
    print("Updated IP from + " + published_ip + " to " + my_public_ip)
    time.sleep(300)


