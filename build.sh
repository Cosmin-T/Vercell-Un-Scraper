#!/usr/bin/env bash
# build.sh
set -o errexit

# Install missing libraries
apt-get update && apt-get install -y \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    libgles2-mesa \
    && rm -rf /var/lib/apt/lists/*

python -m pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright and browsers
PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.playwright playwright install
python -m playwright install

python manage.py collectstatic --noinput
python manage.py migrate
if [[ $CREATE_SUPERUSER ]]
then
    python manage.py createsuperuser --no-input --email ⬤