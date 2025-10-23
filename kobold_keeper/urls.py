"""
URL configuration for the kobold_keeper project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path, include

from api.web_views import HomeView, AboutView, DocsView, LoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('docs/', DocsView.as_view(), name='docs'),
    path('login/', LoginView.as_view(), name='login'),

    path('api/', include('api.urls')),
]
