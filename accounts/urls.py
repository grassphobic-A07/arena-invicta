# accounts/urls.py
from django.urls import path
from .views import register, login_user, logout_user, home, profile_detail, profile_edit, delete_account, delete_avatar

app_name = 'accounts'

urlpatterns = [
    path('', home, name='home'),
    path('register/', register, name='register'),
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout'),
    path('delete/', delete_account, name='delete'),

    # >>> statis lebih dulu
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('profile/avatar/delete/', delete_avatar, name='delete_avatar'),

    # >>> paling akhir: dinamis
    path('profile/<str:username>/', profile_detail, name='profile_detail'),
]
