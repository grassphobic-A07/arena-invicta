# accounts/models.py
from django.contrib.auth.models import User
from django.db import models

# Untuk konfigurasi Profile
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=100, blank=True)
    favorite_team = models.CharField(max_length=100, blank=True)
    avatar_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"Profile({self.user.username})"

