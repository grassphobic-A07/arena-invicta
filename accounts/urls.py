# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import SignUpView

app_name = 'accounts'

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Tambahkan URL untuk reset password jika diperlukan
]