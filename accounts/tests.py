from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User, Group

from .apps import AccountsConfig
from .models import Profile
from .forms import LoginForm, RegisterWithRoleForm, ProfileForm
from . import signals


class AccountsSmokeTests(TestCase):
    def setUp(self):
        # Pastikan default groups ada (cover signals.ensure_groups)
        signals.ensure_groups(sender=None)
        self.client = Client()
        self.rf = RequestFactory()
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(username="alice", password=self.password)

    # ---------- Models ----------
    def test_profile_str(self):
        p = self.user.profile  # dibuat otomatis oleh signal
        self.assertEqual(str(p), "Profile(alice)")

    # ---------- Signals ----------
    def test_post_save_creates_profile_and_adds_registered_group(self):
        u = User.objects.create_user(username="bob", password="AnotherPass123!")
        self.assertTrue(Profile.objects.filter(user=u).exists())
        self.assertIn("Registered", list(u.groups.values_list("name", flat=True)))

    def test_post_migrate_creates_groups(self):
        Group.objects.filter(name__in=["Registered", "Writer", "Editor"]).delete()
        self.assertEqual(Group.objects.filter(name__in=["Registered", "Writer", "Editor"]).count(), 0)
        signals.ensure_groups(sender=None)
        for name in ["Registered", "Writer", "Editor"]:
            self.assertTrue(Group.objects.filter(name=name).exists())

    # ---------- Forms ----------
    def test_login_form_add_error_styles_on_non_field_errors(self):
        # Password salah -> NON_FIELD_ERRORS
        data = {"username": "alice", "password": "wrong"}
        req = self.rf.post(reverse("accounts:login"), data)
        form = LoginForm(req, data=data)
        self.assertFalse(form.is_valid())
        form.add_error_styles()
        self.assertIn("ring-red-200", form.fields["username"].widget.attrs.get("class", ""))
        self.assertIn("ring-red-200", form.fields["password"].widget.attrs.get("class", ""))

    def test_register_form_add_error_styles_on_field_errors(self):
        data = {"username": "newbie", "password1": "short", "password2": "mismatch", "role": "registered"}
        form = RegisterWithRoleForm(data=data)
        self.assertFalse(form.is_valid())
        form.add_error_styles()
        self.assertTrue(any("ring-red-200" in f.widget.attrs.get("class", "") for f in form.fields.values()))

    def test_profile_form_widgets_have_base_classes(self):
        form = ProfileForm()
        for name in ("display_name", "favorite_team", "avatar_url", "bio"):
            self.assertIn("rounded-xl", form.fields[name].widget.attrs.get("class", ""))

    # ---------- Views: register ----------
    def test_register_get(self):
        resp = self.client.get(reverse("accounts:register"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("form", resp.context)

    def test_register_post_invalid_shows_form(self):
        data = {"username": "neo", "password1": "aaa", "password2": "bbb", "role": "registered"}
        resp = self.client.post(reverse("accounts:register"), data)
        self.assertEqual(resp.status_code, 200)  # tetap di halaman form
        self.assertContains(resp, "Password")

    def test_register_post_valid_adds_writer_and_redirects(self):
        data = {"username": "writer1", "password1": "VerySafe123!", "password2": "VerySafe123!", "role": "writer"}
        resp = self.client.post(reverse("accounts:register"), data)
        self.assertIn(resp.status_code, (302, 303))
        u = User.objects.get(username="writer1")
        self.assertIn("Writer", list(u.groups.values_list("name", flat=True)))

    # ---------- Views: login/logout ----------
    def test_login_get(self):
        resp = self.client.get(reverse("accounts:login"))
        self.assertEqual(resp.status_code, 200)

    def test_login_post_invalid_applies_error_styles(self):
        resp = self.client.post(reverse("accounts:login"), {"username": "alice", "password": "nope"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ring-red-200", resp.content.decode())  # form invalid ditandai merah

    def test_login_post_valid_sets_cookie_and_redirects_next(self):
        next_url = reverse("accounts:profile_detail")
        resp = self.client.post(f"{reverse('accounts:login')}?next={next_url}",
                                {"username": "alice", "password": self.password})
        self.assertIn(resp.status_code, (302, 303))
        self.assertEqual(resp.headers.get("Location"), next_url)
        self.assertIn("last_login", resp.cookies)

    def test_logout_deletes_cookie(self):
        self.client.login(username="alice", password=self.password)
        self.client.cookies["last_login"] = "now"
        resp = self.client.get(reverse("accounts:logout"))
        self.assertIn(resp.status_code, (302, 303))
        self.assertIn("last_login", resp.cookies)  # dijadwalkan dihapus

    # ---------- Views: home ----------
    def test_home_anonymous(self):
        resp = self.client.get(reverse("accounts:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["roles"], [])

    def test_home_authenticated(self):
        self.client.login(username="alice", password=self.password)
        resp = self.client.get(reverse("accounts:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Registered", resp.context["roles"])

    # ---------- Views: profile detail ----------
    def test_profile_detail_requires_login(self):
        resp = self.client.get(reverse("accounts:profile_detail"))
        self.assertIn(resp.status_code, (302, 303))
        self.assertIn(reverse("accounts:login"), resp.headers.get("Location"))

    def test_profile_detail_authenticated(self):
        self.client.login(username="alice", password=self.password)
        resp = self.client.get(reverse("accounts:profile_detail"))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.context["profile"], Profile)

    # ---------- Views: profile edit ----------
    def test_profile_edit_get(self):
        self.client.login(username="alice", password=self.password)
        resp = self.client.get(reverse("accounts:profile_edit"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("form", resp.context)

    def test_profile_edit_post_valid_updates(self):
        self.client.login(username="alice", password=self.password)
        data = {
            "display_name": "Alice Z",
            "favorite_team": "Invicta FC",
            "avatar_url": "https://example.com/a.png",
            "bio": "Hi!"
        }
        resp = self.client.post(reverse("accounts:profile_edit"), data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alice Z")
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile.display_name, "Alice Z")

    def test_profile_edit_clear_avatar_on_invalid_url(self):
        """Form invalid + clear_avatar=1 -> branch yang mengosongkan instance.avatar_url"""
        self.client.login(username="alice", password=self.password)
        data = {"display_name": "", "favorite_team": "", "avatar_url": "not-a-url", "bio": "", "clear_avatar": "1"}
        resp = self.client.post(reverse("accounts:profile_edit"), data)
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        self.assertEqual(form.instance.avatar_url, "")

    # ---------- Views: delete ----------
    def test_delete_requires_post_and_deletes(self):
        self.client.login(username="alice", password=self.password)
        resp_get = self.client.get(reverse("accounts:delete"))
        self.assertEqual(resp_get.status_code, 405)  # require_POST

        resp_post = self.client.post(reverse("accounts:delete"))
        self.assertIn(resp_post.status_code, (302, 303))
        self.assertFalse(User.objects.filter(username="alice").exists())


    def test_admin_import(self):
        __import__("accounts.admin")
