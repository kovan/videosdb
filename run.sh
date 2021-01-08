#export AUTOLOGGING_TRACED_NOOP=1 # disable autologging
./manage.py videosdb --check-for-new-videos
./manage.py videosdb --sync-wordpress
