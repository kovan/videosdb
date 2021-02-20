from .settings import *

DATABASES = {

    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'tempdb',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'db',
        'PORT': '',
        'TEST': {
            "NAME": "test_videosdb",
        },
    },
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.local.sqlite3'),
        'TEST': {
            "NAME": "dbtest.sqlite3",
        },
    }
}

VIDEOSDB_DOMAIN = "sadhguru.digital"
VIDEOSDB_DNSZONE = "sadhguru"
YOUTUBE_CHANNEL = {
    "id": "UCcYzLCs3zrQIBVHYA1sK2sw",
    "name": "Sadhguru"
}
TRUNCATE_DESCRIPTION_AFTER = "#Sadhguru"
YOUTUBE_KEY = "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU"
VIDEO_FILES_DIR = "videos"
