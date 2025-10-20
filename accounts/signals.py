# accounts/signals.py
from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import Profile

@receiver(post_migrate)
def ensure_groups_and_bind_news_perms(sender, **kwargs):
    # Pastikan grup utama
    staff, _ = Group.objects.get_or_create(name="Content Staff")
    Group.objects.get_or_create(name="Registered")

    # Kalau app 'news' belum dimigrate, stop
    try:
        ct = ContentType.objects.get(app_label="news", model="article")
    except ContentType.DoesNotExist:
        return

    # Default model perms + custom publish
    # Role sudah aku buat jadi 2. Sekarang content_staff udah Writer + Editor. Dia nantinya bisa 
    # sekaligus nulis & publish di aplikasi News punya Rafa
    # Ini nanti bisa dipanggil di aplikasi News punya Rafa supaya content_staff lah yang dapat publish
    want = ["add_article", "change_article", "delete_article", "view_article", "can_publish"]
    perms = list(Permission.objects.filter(content_type=ct, codename__in=want))
    if perms:
        staff.permissions.add(*perms)

@receiver(post_save, sender=User)
def create_profile_and_register(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        Group.objects.get_or_create(name="Registered")[0].user_set.add(instance)

@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)