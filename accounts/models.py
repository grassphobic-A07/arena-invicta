# accounts/models.py
from django.conf import settings
from django.db import models

ROLE_CHOICES = [
    ("registered", "Registered"),
    ("content_staff", "Content Staff"), # Writer + Editor (boleh publish)
    
]

# Untuk konfigurasi Profile
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=100, blank=True)
    favorite_team = models.CharField(max_length=100, blank=True)
    avatar_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)

    # Hanya 2 role konten
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="registered")

    @property
    def is_content_staff(self) -> bool:
        return self.role == "content_staff"

    @property
    def can_publish_news(self) -> bool:
        # Modul News nanti cukup cek properti ini (Rafa)
        return self.is_content_staff

    def __str__(self):
        return f"Profile({self.user.username})"

