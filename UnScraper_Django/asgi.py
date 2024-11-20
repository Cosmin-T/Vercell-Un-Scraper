import os
from django.core.asgi import get_asgi_application
from django.urls import path
from scraper_app.views import scrape_website

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UnScraper_Django.settings')

application = get_asgi_application()

urlpatterns = [
    path('', scrape_website),
]