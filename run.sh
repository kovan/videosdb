#pipenv activate
#source venv/bin/activate
pipenv shell
pipenv install
#pip install -q -r requirements.freezed.txt
#export AUTOLOGGING_TRACED_NOOP=1 # disable autologging
./manage.py videosdb -t --check-for-new-videos
./manage.py videosdb -t --publish-next
