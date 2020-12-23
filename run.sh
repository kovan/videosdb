export AUTOLOGGING_TRACED_NOOP=1 # disable autologging
source venv/bin/activate
./manage.py videosdb --check-for-new-videos
./manage.py videosdb --sync-wordpress
