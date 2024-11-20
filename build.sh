#!/usr/bin/env bash
# build.sh
set -o errexit

# Install system dependencies for Playwright
apt-get update
apt-get install -y libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libgstreamer-plugins-bad1.0-0 \
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    libgles2 \
    libegl1 \
    libopus0 \
    libwebp7 \
    libwebpdemux2 \
    libwoff1

python -m pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright and browsers
playwright install chromium
python -m playwright install

python manage.py collectstatic --noinput
python manage.py migrate
if [[ $CREATE_SUPERUSER ]]
then
    python manage.py createsuperuser --no-input --email "$DJANGO_SUPERUSER_EMAIL"
fi