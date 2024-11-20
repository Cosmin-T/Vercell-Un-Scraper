#!/usr/bin/env bash
set -o errexit

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers without root
PLAYWRIGHT_SKIP_BROWSER_GC=1 playwright install chromium --with-deps

# Your Django commands
python manage.py collectstatic --noinput
python manage.py migrate