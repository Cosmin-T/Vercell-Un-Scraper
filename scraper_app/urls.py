# scraper_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.scrape_website, name='index'),
    path('download/csv/', views.download_csv, name='download_csv'),
    path('download/json/', views.download_json, name='download_json'),
    path('upload/', views.handle_file_upload, name='handle_file_upload'),
]