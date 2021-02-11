from .settings import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'postgres',
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
        'NAME': os.path.join(BASE_DIR, 'db.sadhguru.sqlite3'),
        'TEST': {
            "NAME": "dbtest.sqlite3",
        },
    }
}


WWW_ROOT = "https://www.sadhguru.digital"
WP_USERNAME = "xaum.io@gmail.com"
WP_PASS = "Hb+d6KAH"
YOUTUBE_CHANNEL = {
    "id": "UCcYzLCs3zrQIBVHYA1sK2sw",
    "name": "Sadhguru"
}
TRUNCATE_DESCRIPTION_AFTER = "#Sadhguru"
YOUTUBE_KEY = "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU"
VIDEO_FILES_DIR = "/mnt/gcs"
