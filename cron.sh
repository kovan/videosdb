#!/bin/bash

cd ~/prj/blog
git pull
source venv/bin/activate
pip install -r requirements.txt
python videos_db.py --verbose --enqueue https://www.youtube.com/user/sadhguru
python videos_db.py --verbose --publish-next
