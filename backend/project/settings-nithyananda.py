from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'nithyananda',
        'USER': 'nithyananda',
        'PASSWORD': 'nithyananda',
        'HOST': 'db',
        'PORT': '',
        'TEST': {
                "NAME": "test_videosdb",
        },
    },
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.nithyananda.sqlite3'),
        'TEST': {
            "NAME": "dbtest.sqlite3",
        },
    }
}

WWW_ROOT = "https://www.nithyananda.yoga"
WP_USERNAME = "nithyananda"
WP_PASS = "P74xhrhtn4WUkX"
YOUTUBE_CHANNEL = {
    "id": "UC9OM-qeiYIPtAkBe9veG5uw",
    "name": "KAILASA's Nithyananda",
}
TRUNCATE_DESCRIPTION_AFTER = r"(c|C)lick http://bit.ly/"
YOUTUBE_KEY = "AIzaSyDmVPLhxiShjGUh0VjkJNHloVrfBg_ZfNE"
