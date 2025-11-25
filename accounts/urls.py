# accounts/urls.py
from django.urls import path
from .views import (edit_profile_api, register, login_user, logout_user, home, 
                    profile_detail, profile_edit, delete_account, delete_avatar, 
                    admin_dashboard, login_api, register_api, user_profile_api_json, logout_api)

app_name = 'accounts'

urlpatterns = [
    path('', home, name='home'),

    # Untuk mengarahkan ke bagian web 
    path('register/', register, name='register'),
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout'),
    path('delete/', delete_account, name='delete'),

    # Untuk mengarahkan ke mobile/JSON Response/API
    # path("api/register/", register, name="api_register"),
    path('api/login/', login_api, name='login_api'),
    path('api/register/', register_api, name='register_api'),
    path('api/logout/', logout_api, name='logout_api'),
    path('api/profile/json/', user_profile_api_json, name='profile_api'),
    path('api/profile/edit/', edit_profile_api, name='edit_profile_api'),   

    # >>> statis lebih dulu
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('profile/avatar/delete/', delete_avatar, name='delete_avatar'),

    # >>> paling akhir: dinamis
    path('profile/<str:username>/', profile_detail, name='profile_detail'),

    # Admin
    path("admin/", admin_dashboard, name="admin_dashboard")
]
