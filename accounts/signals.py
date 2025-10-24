# accounts/signals.py
import os
from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import Profile

# Khusus Admin
@receiver(post_migrate)
def ensure_static_admin(sender, **kwargs):
    # jalan saat migrate app apa pun; batasi hanya sekali untuk project
    # (check label 'accounts' aman, tapi kalau tak pasti—biarkan saja, kodenya idempotent)
    if getattr(sender, "name", "") not in {"accounts"}:
        return

    username = os.getenv("ARENA_ADMIN_USER", "arena_admin")
    password = os.getenv("ARENA_ADMIN_PASS", "ArenaAdmin123!")

    admin_user, created = User.objects.get_or_create(username=username, defaults={"is_active": True})
    if created or not admin_user.has_usable_password():
        admin_user.set_password(password)
    admin_user.is_active = True
    # Tidak pakai Django Admin UI → tak perlu is_staff/is_superuser
    admin_user.save()

    # pastikan profile ada, role kontennya biarkan 'registered' (admin ≠ content_staff)
    Profile.objects.get_or_create(user=admin_user)

# Penting untuk nanti model News (Rafa)
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

# Penting untuk permission model leagues (Naufal)
@receiver(post_migrate)
def ensure_groups_and_bind_leagues_perms(sender, **kwargs):
    # pastikan grup ada
    staff, _ = Group.objects.get_or_create(name="Content Staff")
    registered, _ = Group.objects.get_or_create(name="Registered")

    # ambil content types untuk app 'leagues'
    for model_name in ["league", "team", "match", "standing"]:
        try:
            ct = ContentType.objects.get(app_label="leagues", model=model_name)
        except ContentType.DoesNotExist:
            continue

        # berikan semua model perms ke Content Staff (CRUD + view)
        want_staff = [f"add_{model_name}", f"change_{model_name}", f"delete_{model_name}", f"view_{model_name}"]
        perms_staff = list(Permission.objects.filter(content_type=ct, codename__in=want_staff))
        if perms_staff:
            staff.permissions.add(*perms_staff)

        # Registered: hanya view
        want_reg = [f"view_{model_name}"]
        perms_reg = list(Permission.objects.filter(content_type=ct, codename__in=want_reg))
        if perms_reg:
            registered.permissions.add(*perms_reg)


@receiver(post_save, sender=User)
def create_profile_and_register(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        Group.objects.get_or_create(name="Registered")[0].user_set.add(instance)

@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)