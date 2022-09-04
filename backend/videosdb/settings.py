import os
import sys


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname}\t{asctime}:{name}.{funcName} ({filename}:{lineno:d}): {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname}\t{message}',
            'style': '{',
        },
    },
    'handlers': {
        # 'file': {
        #     'class': 'logging.handlers.RotatingFileHandler',
        #     'maxBytes': 1000000,
        #     "backupCount": 10,
        #     'filename': 'logs/videosdb.log',
        #     'formatter': 'verbose'
        # },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'stream': sys.stderr
        }
    },
    'loggers': {
        'anyio': {
            "level": os.environ.get("LOGLEVEL", "INFO"),
        },

        'asyncio': {
            "level": os.environ.get("LOGLEVEL", "INFO"),
        },
        'videosdb': {
            'handlers': ['console'],
            'level': os.environ.get("LOGLEVEL", "INFO"),
            'propagate': False,
        },
        "property_manager": {
            'handlers': ['console'],
            "level": "INFO",
            'propagate': False,
        },
        '': {
            'handlers': ['console'],
            'level': "INFO",
            'propagate': True
        }
    },
}


IPFS_HOST = os.environ.get("IPFS_HOST", "127.0.0.1")
IPFS_PORT = os.environ.get("IPFS_PORT", 5001)

VIDEOSDB_DOMAIN = "sadhguru.digital"
VIDEOSDB_DNSZONE = "sadhguru"
YOUTUBE_CHANNEL = {
    "id": "UCcYzLCs3zrQIBVHYA1sK2sw",
    "name": "Sadhguru"
}
TRUNCATE_DESCRIPTION_AFTER = "#Sadhguru"
VIDEO_FILES_DIR = "/mnt/videos"


YOUTUBE_KEY = "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU"  # works, primary
# YOUTUBE_KEY = "AIzaSyCRG-LiGKbn0ZFzNUU7qD3nzwkAw8I9Oa4"  # works
# YOUTUBE_KEY = "AIzaSyCvLLl93DvwWg5hnqizEbDz5hBE9fAmXnc" # doesn't work
# YOUTUBE_KEY = "AIzaSyBS_oLkjg3skPbC49VmPit3dPFPPnZDPRQ" # quota exeeded
# YOUTUBE_KEY = "AIzaSyBV1J9SPIGKSpl5nxHdzwS6mx5aIFfjpXE" # invalid key, doesn't work

# works, used for testing, responses in HAR file
YOUTUBE_KEY_TESTING = "AIzaSyDM-rEutI1Mr6_b1Uz8tofj2dDlwcOzkjs"
