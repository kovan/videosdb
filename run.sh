
source venv/bin/activate
pip install -q -r requirements.txt
export AUTOLOGGING_TRACED_NOOP=1 # disable autologging
python videos_db.py  --enqueue https://www.youtube.com/user/sadhguru
python videos_db.py  --enable-ipfs --publish-next
