#!/usr/bin/env bash
set -o errexit

# Add Debian's testing sources for more up-to-date packages
echo "deb http://deb.debian.org/debian testing main" >> /etc/apt/sources.list

# Install required system dependencies
apt-get update && apt-get install -y \
    gstreamer1.0-libav \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    libgstreamer-plugins-base1.0-0 \
    libgstreamer1.0-0 \
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    libegl1 \
    libgl1 \
    libgles2 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright with dependencies
PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/.playwright playwright install --with-deps chromium

# Your Django commands
python manage.py collectstatic --noinput
python manage.py migrate