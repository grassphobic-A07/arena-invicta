from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from .models import Profile

@receiver(post_migrate)
def ensure_groups(sender, **kwargs):
    # Dipanggil habis migrate; pastiin groups ada
    for name in ["Registered", "Writer", "Editor"]:
        Group.objects.get_or_create(name=name)

@receiver(post_save, sender=User)
def create_profile_and_register(sender, instance, created, **kwargs):
    # User baru otomatis masuk group Registered
    if created:
        Profile.objects.create(user=instance)
        Group.objects.get_or_create(name="Registered")[0].user_set.add(instance)
