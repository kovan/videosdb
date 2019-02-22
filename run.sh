pipenv run pipenv install
export AUTOLOGGING_TRACED_NOOP=1 # disable autologging
pipenv run python manage.py videosdb --check-for-new-videos
pipenv run python manage.py videosdb --publish-next
