export AUTOLOGGING_TRACED_NOOP=1 # disable autologging
export GOOGLE_APPLICATION_CREDENTIALS=creds.json
pipenv run pipenv install > /dev/null
pipenv run python manage.py videosdb --check-for-new-videos
pipenv run python manage.py videosdb --publish-next
