#!/usr/bin/env bash
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

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright and its browsers
python -m playwright install

# Collect static files and run migrations
python manage.py collectstatic --noinput
python manage.py migrate