#!/usr/bin/env bash
# build.sh
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --noinput