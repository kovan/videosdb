
source venv/bin/activate
pip install -q -r requirements.freezed.txt
#export AUTOLOGGING_TRACED_NOOP=1 # disable autologging
./manage.py videosdb -t -v --enqueue
./manage.py videosdb -t -v --publish-next
