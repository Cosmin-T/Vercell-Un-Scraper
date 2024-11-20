#!/bin/bash
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Install only Chromium browser
playwright install chromium

# Run Django commands
python manage.py collectstatic --noinput
python manage.py migrate