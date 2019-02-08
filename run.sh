
source venv/bin/activate
pip install -q -r requirements.freezed.txt
#export AUTOLOGGING_TRACED_NOOP=1 # disable autologging
python videos_db.py -t -v --enqueue https://www.youtube.com/user/sadhguru
python videos_db.py -t -v --publish-next
