#export AUTOLOGGING_TRACED_NOOP=1 # disable autologging
poetry run python manage.py videosdb --check-for-new-videos
poetry run python manage.py videosdb --sync-wordpress
