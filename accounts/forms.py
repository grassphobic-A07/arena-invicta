# accounts/forms.py
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # Tentukan field apa saja yang muncul di form registrasi
        fields = ('username', 'email')