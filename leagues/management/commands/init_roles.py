from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType

from leagues.models import League, Team, Match, Standing

class Command(BaseCommand):
    help = "Initialize role groups and assign model permissions"

    def handle(self, *args, **options):
        # content types leagues app
        ct_league = ContentType.objects.get_for_model(League)
        ct_team   = ContentType.objects.get_for_model(Team)
        ct_match  = ContentType.objects.get_for_model(Match)
        ct_stand  = ContentType.objects.get_for_model(Standing)

        # content types auth app (untuk kelola akun)
        ct_user   = ContentType.objects.get_for_model(User)
        # Group model dari auth
        from django.contrib.auth.models import Group as AuthGroup
        ct_group  = ContentType.objects.get_for_model(AuthGroup)

        def perms(ct, *codes):
            return list(Permission.objects.filter(content_type=ct, codename__in=codes))

        # --- Visitor: tidak perlu group (akses publik saja) ---

        # --- Registered User: optional (tidak akses admin) ---
        reg, _ = Group.objects.get_or_create(name="Registered User")
        # Tambahkan 'view' jika ingin beri akses baca via admin (biasanya tidak perlu):
        # reg.permissions.add(*perms(ct_match, "view_match"), *perms(ct_stand, "view_standing"))

        # --- Editor: kelola konten leagues ---
        editor, _ = Group.objects.get_or_create(name="Editor")
        # League: view + add + change (tanpa delete)
        editor.permissions.add(*perms(ct_league, "view_league", "add_league", "change_league"))
        # Team: full CRUD
        editor.permissions.add(*perms(ct_team, "view_team", "add_team", "change_team", "delete_team"))
        # Match: full CRUD
        editor.permissions.add(*perms(ct_match, "view_match","add_match","change_match","delete_match"))
        # Standing: view only (ubah sesuai kebutuhan)
        editor.permissions.add(*perms(ct_stand, "view_standing"))

        # --- Administrator: hanya boleh kelola AKUN (user & group), TIDAK boleh konten leagues ---
        admin_group, _ = Group.objects.get_or_create(name="Administrator")
        # berikan hak atas user & group
        admin_group.permissions.add(
            *perms(ct_user,  "view_user", "add_user", "change_user", "delete_user"),
            *perms(ct_group, "view_group","add_group","change_group","delete_group"),
        )
        # PASTIKAN tidak menambahkan permission leagues apa pun ke Administrator!

        self.stdout.write(self.style.SUCCESS("Roles initialized: Registered User, Editor, Administrator (accounts-only)"))
