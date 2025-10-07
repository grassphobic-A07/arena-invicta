# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('member', 'Anggota Arena'),
        ('writer', 'Penulis'),
        ('editor', 'Editor'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    
    def __str__(self):
        return self.username