# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import register, login_user, logout_user, home

app_name = 'accounts'

urlpatterns = [
    # Halaman beranda, kalo berhasil login
    path('', home, name='home'),
    path('register/', register, name='register'),
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout'),
]