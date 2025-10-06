from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('docs/', views.docs, name='docs'),
    path('login/', views.login, name='login'),
]