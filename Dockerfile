FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Set work directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files and run migrations
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate

# Run gunicorn
CMD gunicorn UnScraper_Django.wsgi:app --bind 0.0.0.0:$PORT