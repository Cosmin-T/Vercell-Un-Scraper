#!/usr/bin/env bash
# build.sh
set -o errexit

python -m pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright with system dependencies
PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.playwright pip install playwright
PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.playwright playwright install chromium

python manage.py collectstatic --noinput
python manage.py migrate
if [[ $CREATE_SUPERUSER ]]
then
    python manage.py createsuperuser --no-input --email "$DJANGO_SUPERUSER_EMAIL"
fi