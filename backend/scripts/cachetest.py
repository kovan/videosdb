
import json
import httplib2
from django.core.cache import cache


def run():

    http = httplib2.Http(cache)

    with open("urls.txt", "r") as a_file:
        for line in a_file:
            stripped_line = line.strip()
            print(stripped_line)
            http.request(stripped_line)
