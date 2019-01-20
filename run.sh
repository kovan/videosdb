
source venv/bin/activate
pip install -q -r requirements.txt
python videos_db.py --verbose --enqueue https://www.youtube.com/user/sadhguru
python videos_db.py --verbose --ipfs-enable --publish-next
