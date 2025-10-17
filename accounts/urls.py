# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import register, login_user, logout_user, home, profile_detail, profile_edit, delete_account

app_name = 'accounts'

urlpatterns = [
    # Halaman beranda, kalo berhasil login
    path('', home, name='home'),
    path('register/', register, name='register'),
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout'),
    path('profile', profile_detail, name='profile_detail'),
    path("profile/edit/", profile_edit, name="profile_edit"),
    path("delete/", delete_account, name="delete"),
]