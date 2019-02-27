export AUTOLOGGING_TRACED_NOOP=1 # disable autologging
export GOOGLE_APPLICATION_CREDENTIALS=creds.json
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.freezed.txt
./manage.py videosdb -t --check-for-new-videos
./manage.py videosdb -t --publish-next
