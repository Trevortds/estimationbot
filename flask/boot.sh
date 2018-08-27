#!/bin/sh

chmod 777 /home/scrumbot/data

flask db upgrade

python -m flask run --host=0.0.0.0
