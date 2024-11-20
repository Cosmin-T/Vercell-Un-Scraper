#!/usr/bin/env bash
# build.sh
set -o errexit

python -m pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
python -m playwright install

python manage.py collectstatic --noinput
python manage.py migrate
if [[ $CREATE_SUPERUSER ]]
then
    python manage.py createsuperuser --no-input --email "$DJANGO_SUPERUSER_EMAIL"
fi