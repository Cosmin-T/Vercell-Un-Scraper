#!/usr/bin/env bash
# build.sh
set -o errexit

python -m pip install --upgrade pip
pip install -r requirements.txt

# Install browser dependencies with sudo
sudo playwright install-deps

# Then install browser
PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.playwright playwright install chromium
python -m playwright install

python manage.py collectstatic --noinput
python manage.py migrate
if [[ $CREATE_SUPERUSER ]]
then
    python manage.py createsuperuser --no-input --email "$DJANGO_SUPERUSER_EMAIL"
fi