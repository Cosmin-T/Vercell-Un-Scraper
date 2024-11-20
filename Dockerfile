# Use Node.js Playwright image as base
FROM mcr.microsoft.com/playwright:v1.40.0-focal

# Install Python
RUN apt-get update && apt-get install -y python3 python3-pip

# Set work directory
WORKDIR /app

# Copy requirements first
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy project files
COPY . .

# Run migrations and collect static
RUN python3 manage.py migrate
RUN python3 manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Start command
CMD ["gunicorn", "UnScraper_Django.wsgi:application", "--bind", "0.0.0.0:$PORT"]
