#!/bin/bash

cd ~/prj/blog
git pull
source venv/bin/activate
/videos_db.py --enqueue https://www.youtube.com/user/sadhguru
/videos_db.py --publish-next
