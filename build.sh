#!/usr/bin/env bash
# build.sh
set -o errexit

python -m pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright with xvfb for Render
pip install playwright
pip install pytest-playwright
playwright install chromium
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
apt-get update
apt-get install -y google-chrome-stable

python manage.py collectstatic --noinput
python manage.py migrate
if [[ $CREATE_SUPERUSER ]]
then
    python manage.py createsuperuser --no-input --email "$DJANGO_SUPERUSER_EMAIL"
fi