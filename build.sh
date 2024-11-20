#!/usr/bin/env bash
# build.sh
set -o errexit

python -m pip install --upgrade pip
pip install -r requirements.txt

# Install required system dependencies
apt-get update && apt-get install -y \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    libegl1 \
    libgles2

# Install Playwright and browsers
PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.playwright playwright install chromium
python -m playwright install

python manage.py collectstatic --noinput
python manage.py migrate
if [[ $CREATE_SUPERUSER ]]
then
    python manage.py createsuperuser --no-input --email "$DJANGO_SUPERUSER_EMAIL"
fi