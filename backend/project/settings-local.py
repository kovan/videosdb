from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.local.sqlite3'),
        'TEST': {
            "NAME": "dbtest.sqlite3",
        },
    }
}

# WWW_ROOT = "https://www.sadhguru.digital"
# WP_USERNAME = "xaum.io@gmail.com"
# WP_PASS = "Hb+d6KAH"
YOUTUBE_CHANNEL = {
    "id": "UCcYzLCs3zrQIBVHYA1sK2sw",
    "name": "Sadhguru"
}
TRUNCATE_DESCRIPTION_AFTER = "#Sadhguru"
