# leagues/tests.py

import datetime
import json # <-- Tambahkan untuk tes AJAX
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError
from django.contrib.messages import get_messages
from django.contrib import admin
from unittest.mock import patch

from .models import League, Team, Match, Standing
from .forms import MatchUpdateForm, MatchCreateForm
from .services import recompute_standings_for_league
# Import admin models untuk diuji
from .admin import LeagueAdmin, TeamAdmin, MatchAdmin, StandingAdmin
# Import view untuk tes AJAX langsung (opsional, tapi bisa berguna)
from .views import _is_ajax

from io import StringIO
from django.core.management import call_command, CommandError
from django.contrib.auth.models import Group
import tempfile
import os

# Fungsi helper untuk membuat data dummy agar tidak duplikat
def create_test_data():
    """Menciptakan data awal untuk tes."""
    # 1. Buat User
    user = User.objects.create_user(username='testuser', password='password123')
    # Buat staff user dengan profil
    staff_user = User.objects.create_user(username='staffuser', password='password123')
    # Tambahkan profile ke staff user (asumsi signal tidak berjalan di test atau perlu eksplisit)
    # Jika menggunakan signals.py untuk membuat Profile dan Group, ini mungkin tidak perlu
    # tapi lebih aman untuk memastikan state di test
    from accounts.models import Profile, ROLE_CHOICES
    Profile.objects.get_or_create(user=staff_user, defaults={'role': 'content_staff'})

    superuser = User.objects.create_superuser(username='admin', password='password123')
    Profile.objects.get_or_create(user=superuser) # Pastikan admin juga punya profil

    # Beri permission ke staff user (opsional, tergantung tes permission)
    # Misal, beri semua permission Match
    # content_type = ContentType.objects.get_for_model(Match)
    # match_permissions = Permission.objects.filter(content_type=content_type)
    # staff_user.user_permissions.add(*match_permissions)


    # 2. Buat League dan Team
    league = League.objects.create(name="Test League", country="Testland")
    t1 = Team.objects.create(league=league, name="Alpha Team")
    t2 = Team.objects.create(league=league, name="Bravo Team")
    t3 = Team.objects.create(league=league, name="Charlie Team")

    # 3. Buat Match
    now = timezone.now()
    past_date = now - datetime.timedelta(days=1)
    future_date = now + datetime.timedelta(days=1)

    # Season 2024/2025 (Finished)
    m1 = Match.objects.create(
        league=league, season="2024/2025", date=past_date,
        home_team=t1, away_team=t2, status=Match.Status.FINISHED,
        home_score=3, away_score=1 # T1 Win, T2 Loss
    )
    m2 = Match.objects.create(
        league=league, season="2024/2025", date=past_date - datetime.timedelta(days=1),
        home_team=t1, away_team=t3, status=Match.Status.FINISHED,
        home_score=1, away_score=1 # T1 Draw, T3 Draw
    )
    m3 = Match.objects.create(
        league=league, season="2024/2025", date=past_date - datetime.timedelta(days=2),
        home_team=t2, away_team=t3, status=Match.Status.FINISHED,
        home_score=0, away_score=2 # T2 Loss, T3 Win
    )

    # Season 2024/2025 (Upcoming)
    m_upcoming = Match.objects.create(
        league=league, season="2024/2025", date=future_date,
        home_team=t1, away_team=t2, status=Match.Status.SCHEDULED
    )

    # Season 2023/2024 (Finished)
    m_old = Match.objects.create(
        league=league, season="2023/2024", date=past_date - datetime.timedelta(days=365),
        home_team=t1, away_team=t2, status=Match.Status.FINISHED,
        home_score=5, away_score=0 # T1 Win
    )

    return {
        'user': user, 'staff': staff_user, 'superuser': superuser,
        'league': league, 't1': t1, 't2': t2, 't3': t3,
        'm1': m1, 'm2': m2, 'm3': m3, # Tambahkan m2, m3 jika perlu
        'm_upcoming': m_upcoming, 'm_old': m_old
    }


class ModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        data = create_test_data()
        cls.league = data['league']
        cls.t1 = data['t1']
        cls.t2 = data['t2'] # Tambahkan t2 untuk tes constraint
        cls.m1 = data['m1']

        # Jalankan recompute agar standing ada
        recompute_standings_for_league(cls.league)
        cls.standing = Standing.objects.get(
            league=cls.league, season="2024/2025", team=cls.t1
        )

    def test_model_str_methods(self):
        self.assertEqual(str(self.league), "Test League")
        self.assertEqual(str(self.t1), "Alpha Team")

        date_str = self.m1.date.strftime("%Y-%m-%d")
        expected_match_str = f"[{self.m1.season}] {self.m1.home_team} vs {self.m1.away_team} ({date_str})"
        self.assertEqual(str(self.m1), expected_match_str)

        expected_standing_str = f"[{self.standing.season}] {self.standing.team.name} - {self.standing.points} pts"
        self.assertEqual(str(self.standing), expected_standing_str)

    def test_match_not_same_team_constraint(self):
        """Tes constraint CheckConstraint(check=~Q(home_team=F('away_team')))"""
        with self.assertRaises(IntegrityError):
            Match.objects.create(
                league=self.league, season="2024/2025", date=timezone.now(),
                home_team=self.t1, away_team=self.t1, # Tim sama
                status=Match.Status.SCHEDULED
            )

    def test_team_unique_together_constraint(self):
        """Tes constraint unique_together = ('league', 'name')"""
        with self.assertRaises(IntegrityError):
            Team.objects.create(league=self.league, name="Alpha Team") # Nama tim sama di liga yang sama

    def test_standing_unique_together_constraint(self):
        """Tes constraint unique_together = ('league', 'season', 'team')"""
        with self.assertRaises(IntegrityError):
            Standing.objects.create(
                league=self.league, season="2024/2025", team=self.t1, points=10
            ) # Standing duplikat

    def test_match_status_choices(self):
        """Tes enum Status di model Match."""
        self.assertEqual(Match.Status.SCHEDULED, "SCHEDULED")
        self.assertEqual(Match.Status.LIVE, "LIVE")
        self.assertEqual(Match.Status.FINISHED, "FINISHED")
        self.assertEqual(Match.Status.POSTPONED, "POSTPONED")
        self.assertIn(("SCHEDULED", "Scheduled"), Match.Status.choices)


class ServicesTests(TestCase):
    def setUp(self):
        self.data = create_test_data()
        self.league = self.data['league']
        self.t1 = self.data['t1']
        self.t2 = self.data['t2']
        self.t3 = self.data['t3']
        # Hapus standing awal jika ada, agar recompute bersih
        Standing.objects.filter(league=self.league).delete()

    def test_recompute_standings_logic(self):
        """Tes logika perhitungan di recompute_standings_for_league."""
        # Data awal: m1(t1 3-1 t2), m2(t1 1-1 t3), m3(t2 0-2 t3), m_old(t1 5-0 t2)
        recompute_standings_for_league(self.league)

        # Harus ada 5 standing: 3 di 24/25, 2 di 23/24
        self.assertEqual(Standing.objects.count(), 5)
        self.assertEqual(Standing.objects.filter(season="2024/2025").count(), 3)
        self.assertEqual(Standing.objects.filter(season="2023/2024").count(), 2)

        # Cek detail standing 2024/2025
        s_t1 = Standing.objects.get(team=self.t1, season="2024/2025")
        s_t2 = Standing.objects.get(team=self.t2, season="2024/2025")
        s_t3 = Standing.objects.get(team=self.t3, season="2024/2025")

        # T1: 1 Win (vs t2), 1 Draw (vs t3) -> Pts=4, P=2, W=1, D=1, L=0, GF=4, GA=2, GD=2
        self.assertEqual(s_t1.points, 4)
        self.assertEqual(s_t1.played, 2)
        self.assertEqual(s_t1.win, 1); self.assertEqual(s_t1.draw, 1); self.assertEqual(s_t1.loss, 0)
        self.assertEqual(s_t1.gf, 4); self.assertEqual(s_t1.ga, 2); self.assertEqual(s_t1.gd, 2)

        # T2: 1 Loss (vs t1), 1 Loss (vs t3) -> Pts=0, P=2, W=0, D=0, L=2, GF=1, GA=5, GD=-4
        self.assertEqual(s_t2.points, 0)
        self.assertEqual(s_t2.played, 2)
        self.assertEqual(s_t2.win, 0); self.assertEqual(s_t2.draw, 0); self.assertEqual(s_t2.loss, 2)
        self.assertEqual(s_t2.gf, 1); self.assertEqual(s_t2.ga, 5); self.assertEqual(s_t2.gd, -4)

        # T3: 1 Draw (vs t1), 1 Win (vs t2) -> Pts=4, P=2, W=1, D=1, L=0, GF=3, GA=1, GD=2
        self.assertEqual(s_t3.points, 4)
        self.assertEqual(s_t3.played, 2)
        self.assertEqual(s_t3.win, 1); self.assertEqual(s_t3.draw, 1); self.assertEqual(s_t3.loss, 0)
        self.assertEqual(s_t3.gf, 3); self.assertEqual(s_t3.ga, 1); self.assertEqual(s_t3.gd, 2)

        # Cek detail standing 2023/2024 (hanya m_old)
        s_t1_old = Standing.objects.get(team=self.t1, season="2023/2024")
        s_t2_old = Standing.objects.get(team=self.t2, season="2023/2024")

        # T1: 1 Win -> Pts=3, P=1, W=1, D=0, L=0, GF=5, GA=0, GD=5
        self.assertEqual(s_t1_old.points, 3)
        self.assertEqual(s_t1_old.played, 1); self.assertEqual(s_t1_old.win, 1)
        self.assertEqual(s_t1_old.gf, 5); self.assertEqual(s_t1_old.ga, 0); self.assertEqual(s_t1_old.gd, 5)

        # T2: 1 Loss -> Pts=0, P=1, W=0, D=0, L=1, GF=0, GA=5, GD=-5
        self.assertEqual(s_t2_old.points, 0)
        self.assertEqual(s_t2_old.played, 1); self.assertEqual(s_t2_old.loss, 1)
        self.assertEqual(s_t2_old.gf, 0); self.assertEqual(s_t2_old.ga, 5); self.assertEqual(s_t2_old.gd, -5)

        # --- Tes Idempotency ---
        # Tambah match baru di 24/25: t1 2-2 t2 (Draw)
        Match.objects.create(
            league=self.league, season="2024/2025", date=timezone.now() - datetime.timedelta(days=3),
            home_team=self.t1, away_team=self.t2, status=Match.Status.FINISHED,
            home_score=2, away_score=2
        )
        recompute_standings_for_league(self.league) # Panggil lagi

        # Jumlah standing harus tetap sama (karena season dan tim tidak berubah)
        self.assertEqual(Standing.objects.count(), 5)

        # Cek ulang standing 2024/2025 setelah match baru
        s_t1_new = Standing.objects.get(team=self.t1, season="2024/2025")
        s_t2_new = Standing.objects.get(team=self.t2, season="2024/2025")

        # T1: Pts awal 4 + 1 (draw baru) = 5
        self.assertEqual(s_t1_new.points, 5)
        self.assertEqual(s_t1_new.played, 3) # Bertambah 1
        self.assertEqual(s_t1_new.draw, 2) # Draw bertambah 1
        self.assertEqual(s_t1_new.gd, 2) # GD tidak berubah (2-2)

        # T2: Pts awal 0 + 1 (draw baru) = 1
        self.assertEqual(s_t2_new.points, 1)
        self.assertEqual(s_t2_new.played, 3) # Bertambah 1
        self.assertEqual(s_t2_new.draw, 1) # Draw bertambah 1
        self.assertEqual(s_t2_new.gd, -4) # GD tidak berubah (2-2)


class FormsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = create_test_data()
        cls.league = cls.data['league']
        cls.t1 = cls.data['t1']
        cls.t2 = cls.data['t2']

        cls.other_league = League.objects.create(name="Other League")
        cls.t_other = Team.objects.create(league=cls.other_league, name="Other Team")

    # --- MatchUpdateForm Tests ---
    def test_match_update_form_valid(self):
        """Tes form valid dengan data minimal."""
        form = MatchUpdateForm(data={
            'home_score': 1, 'away_score': 0, 'status': Match.Status.FINISHED
        })
        self.assertTrue(form.is_valid())

    def test_match_update_form_invalid_score(self):
        """Tes validasi skor negatif (clean_home_score, clean_away_score)."""
        form_neg_home = MatchUpdateForm(data={
            'home_score': -1, 'away_score': 1, 'status': Match.Status.LIVE
        })
        self.assertFalse(form_neg_home.is_valid())
        self.assertIn("Skor home tidak boleh negatif", form_neg_home.errors['home_score'])

        form_neg_away = MatchUpdateForm(data={
            'home_score': 1, 'away_score': -1, 'status': Match.Status.LIVE
        })
        self.assertFalse(form_neg_away.is_valid())
        self.assertIn("Skor away tidak boleh negatif", form_neg_away.errors['away_score'])

    def test_match_update_form_invalid_none_score(self):
        """Tes validasi skor None (clean_home_score, clean_away_score)."""
        # Forms.py baris 12 & 18: `if v is None or v < 0:`
        form_none_home = MatchUpdateForm(data={
            'home_score': None, 'away_score': 1, 'status': Match.Status.LIVE
        })
        self.assertFalse(form_none_home.is_valid())
        self.assertIn("Skor home tidak boleh negatif", form_none_home.errors['home_score'])

        form_none_away = MatchUpdateForm(data={
            'home_score': 1, 'away_score': None, 'status': Match.Status.LIVE
        })
        self.assertFalse(form_none_away.is_valid())
        self.assertIn("Skor away tidak boleh negatif", form_none_away.errors['away_score'])

    def test_match_update_form_clean_max_score(self):
        """Tes validasi skor > 99 (metode clean)."""
        # Forms.py baris 24-28: `if cleaned.get(k) is not None and cleaned[k] > 99:`
        form_max_home = MatchUpdateForm(data={
            'home_score': 100, 'away_score': 1, 'status': Match.Status.FINISHED
        })
        self.assertFalse(form_max_home.is_valid())
        self.assertIn("Skor terlalu besar (maksimal 99)", form_max_home.errors['home_score'])

        form_max_away = MatchUpdateForm(data={
            'home_score': 1, 'away_score': 100, 'status': Match.Status.FINISHED
        })
        self.assertFalse(form_max_away.is_valid())
        self.assertIn("Skor terlalu besar (maksimal 99)", form_max_away.errors['away_score'])

    # --- MatchCreateForm Tests ---
    def test_match_create_form_init_queryset(self):
        """Tes __init__ memfilter queryset home_team & away_team berdasarkan liga."""
        # Forms.py baris 41-44
        form = MatchCreateForm(league=self.league)
        # Harusnya hanya tim dari self.league (t1, t2, t3)
        self.assertEqual(form.fields['home_team'].queryset.count(), 3)
        self.assertCountEqual(
            list(form.fields['home_team'].queryset.values_list('pk', flat=True)),
            [self.t1.pk, self.t2.pk, self.data['t3'].pk] # Gunakan data['t3']
        )
        self.assertEqual(form.fields['away_team'].queryset.count(), 3)

        # Tes dengan liga lain
        form_other = MatchCreateForm(league=self.other_league)
        # Harusnya hanya tim dari self.other_league (t_other)
        self.assertEqual(form_other.fields['home_team'].queryset.count(), 1)
        self.assertEqual(form_other.fields['home_team'].queryset.first(), self.t_other)

    def test_match_create_form_clean_validations(self):
        """Tes metode clean: tim sama dan beda liga."""
        base_data = {
            'season': '2025/2026',
            'date': timezone.now() + datetime.timedelta(days=1), # Pastikan tanggal valid
            'status': Match.Status.SCHEDULED,
            'home_score': None, # Skor bisa None/kosong untuk SCHEDULED
            'away_score': None
        }

        # Tes valid
        form_valid = MatchCreateForm(data=base_data | {'home_team': self.t1.pk, 'away_team': self.t2.pk}, league=self.league)
        self.assertTrue(form_valid.is_valid())

        # Tes invalid: home_team == away_team
        # Forms.py baris 51: `if ht == at:`
        form_same = MatchCreateForm(data=base_data | {'home_team': self.t1.pk, 'away_team': self.t1.pk}, league=self.league)
        self.assertFalse(form_same.is_valid())
        self.assertIn("Tim kandang dan tamu tidak boleh sama", form_same.errors['__all__'] if '__all__' in form_same.errors else form_same.errors.get('away_team', []))

        # Tes invalid: tim beda liga
        # Forms.py baris 53: `if ht.league_id != at.league_id:`
        form_diff = MatchCreateForm(data=base_data | {'home_team': self.t1.pk, 'away_team': self.t_other.pk}, league=self.league)
        # Perlu set queryset manual karena form tidak tahu semua tim saat init di tes
        form_diff.fields['away_team'].queryset = Team.objects.all()
        self.assertFalse(form_diff.is_valid())
        self.assertIn("Kedua tim harus berasal dari liga yang sama", form_diff.errors['__all__'] if '__all__' in form_diff.errors else form_diff.errors.get('away_team', []))


# Helper untuk tes view yang butuh login staff
def staff_only_test(view_name, kwargs=None, method='get', data=None, ajax=False):
    """Decorator atau helper untuk menguji akses view staff."""
    def decorator(test_func):
        def wrapper(self, *args, **test_kwargs):
            url = reverse(view_name, kwargs=kwargs)
            login_url_base = reverse('accounts:login') # Asumsi nama URL login
            login_url_with_next = f'{login_url_base}?next={url}'

            headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'} if ajax else {}

            # 1. Tes akses anonim -> redirect ke login
            client_anon = Client()
            response_anon = getattr(client_anon, method)(url, data=data, **headers)
            if ajax and method == 'post': # AJAX POST redirect jadi 200 OK dgn data khusus, atau 403
                 # Jika view pakai LoginRequiredMixin AJAX-aware, bisa 403 atau JSON redirect
                 if response_anon.status_code == 403:
                     pass # OK, forbidden
                 elif response_anon.status_code == 200:
                     try:
                         # Cek jika view AJAX mengembalikan JSON untuk redirect
                         json_data = response_anon.json()
                         self.assertIn('redirect_url', json_data)
                         self.assertTrue(login_url_base in json_data['redirect_url'])
                     except json.JSONDecodeError:
                         self.fail(f"AJAX POST anonim ke {url} tidak redirect atau 403, malah {response_anon.status_code}")
                 else:
                     self.fail(f"AJAX POST anonim ke {url} tidak redirect atau 403, malah {response_anon.status_code}")
            elif not ajax: # Non-AJAX redirect biasa
                self.assertRedirects(response_anon, login_url_with_next, msg_prefix=f"Anon {method.upper()} {url}")

            # 2. Tes akses user biasa (non-staff) -> redirect ke login atau 403
            client_user = Client()
            client_user.login(username=self.data['user'].username, password='password123')
            response_user = getattr(client_user, method)(url, data=data, **headers)
            # UserPassesTestMixin biasanya redirect, tapi bisa 403 jika raise_exception=True
            if response_user.status_code == 403:
                pass # OK, forbidden
            elif ajax and method == 'post':
                 if response_user.status_code == 403:
                     pass # OK, forbidden
                 elif response_user.status_code == 200:
                     try:
                         json_data = response_user.json()
                         self.assertIn('redirect_url', json_data)
                         self.assertTrue(login_url_base in json_data['redirect_url'])
                     except json.JSONDecodeError:
                          self.fail(f"AJAX POST user biasa ke {url} tidak redirect atau 403, malah {response_user.status_code}")
                 else:
                      self.fail(f"AJAX POST user biasa ke {url} tidak redirect atau 403, malah {response_user.status_code}")

            elif not ajax:
                # Periksa apakah redirect ke login atau halaman lain (misal home jika permission denied)
                # LoginRequiredMixin + UserPassesTestMixin defaultnya redirect ke login
                 self.assertTrue(response_user.url.startswith(login_url_base),
                                msg=f"User biasa {method.upper()} {url} tidak redirect ke login atau 403")


            # 3. Tes akses staff -> harusnya OK (status 200 atau redirect setelah POST)
            client_staff = Client()
            client_staff.login(username=self.data['staff'].username, password='password123')
            response_staff = getattr(client_staff, method)(url, data=data, **headers)
            if method == 'get':
                 if ajax: # GET AJAX bisa 200 (render partial)
                    self.assertEqual(response_staff.status_code, 200, msg_prefix=f"Staff GET AJAX {url}")
                 else: # GET non-AJAX harus 200
                    self.assertEqual(response_staff.status_code, 200, msg_prefix=f"Staff GET {url}")

            elif method == 'post':
                if ajax: # POST AJAX harus 200 OK (jika valid) atau 400 (jika invalid) atau 500 (server error)
                    self.assertIn(response_staff.status_code, [200, 400, 500], msg_prefix=f"Staff POST AJAX {url}")
                    # Jika 200, cek struktur JSON (misal, ada 'Ok' dan 'redirect_url'/'message')
                    if response_staff.status_code == 200:
                        try:
                            json_data = response_staff.json()
                            self.assertIn('Ok', json_data)
                        except json.JSONDecodeError:
                             self.fail(f"Staff POST AJAX {url} sukses (200) tapi response bukan JSON valid")
                else: # POST non-AJAX harus redirect (302) jika valid, atau 200 jika invalid
                    self.assertIn(response_staff.status_code, [200, 302], msg_prefix=f"Staff POST {url}")

            # Panggil fungsi tes asli dengan response staff
            test_func(self, response_staff, *args, **test_kwargs)

        return wrapper
    # Jika decorator, gunakan @staff_only_test(...) di atas metode tes
    # Jika helper, panggil di dalam metode tes: staff_only_test(...)(lambda self, response: ...)
    return decorator


class ViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = create_test_data()
        cls.league = cls.data['league']
        cls.t1 = cls.data['t1']
        cls.t2 = cls.data['t2'] # Butuh t2 untuk tes
        cls.t3 = cls.data['t3'] # Butuh t3 untuk tes
        cls.m1 = cls.data['m1']
        cls.m_upcoming = cls.data['m_upcoming']
        cls.m_old = cls.data['m_old']
        recompute_standings_for_league(cls.league) # Pastikan standing ada

    def setUp(self):
        # Client biasa (anonim)
        self.client = Client()
        # Client user staff yang sudah login
        self.staff_client = Client()
        self.staff_client.login(username=self.data['staff'].username, password='password123')
        # Client user biasa yang sudah login
        self.user_client = Client()
        self.user_client.login(username=self.data['user'].username, password='password123')
        # Header untuk request AJAX
        self.ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

    # === Tes Helper Internal ===
    def test_is_ajax_helper(self):
        """Tes fungsi helper _is_ajax di views.py."""
        rf = RequestFactory()
        request_ajax = rf.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request_normal = rf.get('/')
        self.assertTrue(_is_ajax(request_ajax))
        self.assertFalse(_is_ajax(request_normal))

    # === Tes View Publik (Data Populated) ===

    def test_league_redirect_view(self):
        """Tes view league_list yang redirect ke liga pertama atau home."""
        response = self.client.get(reverse('leagues:league_list'))
        # Harusnya redirect ke dashboard liga pertama
        self.assertRedirects(response, reverse('leagues:league_dashboard', kwargs={'pk': self.league.pk}))

        # Tes kasus tidak ada liga
        League.objects.all().delete()
        response_no_league = self.client.get(reverse('leagues:league_list'))
        # Harusnya redirect ke home (accounts:home) dengan pesan
        self.assertRedirects(response_no_league, reverse('accounts:home'))
        messages = list(get_messages(response_no_league.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Belum ada data liga untuk ditampilkan.")
        # Kembalikan liga untuk tes lain
        self.league = League.objects.create(name="Test League", country="Testland")


    def test_league_dashboard_view(self):
        """Tes detail dashboard liga."""
        url = reverse('leagues:league_dashboard', kwargs={'pk': self.league.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leagues/league_dashboard.html')
        self.assertEqual(response.context['league'], self.league)
        # Cek konteks penting
        self.assertEqual(response.context['latest_season'], '2024/2025')
        self.assertEqual(len(response.context['standings']), 3) # t1, t2, t3
        self.assertEqual(len(response.context['finished_recent']), 3) # m1, m2, m3
        self.assertEqual(len(response.context['upcoming']), 1) # m_upcoming

    def test_match_list_view_and_filters(self):
        """Tes daftar pertandingan dengan berbagai filter GET."""
        url = reverse('leagues:match_list', kwargs={'pk': self.league.pk})

        # Tes tanpa filter (all)
        response_all = self.client.get(url)
        self.assertEqual(response_all.status_code, 200)
        self.assertTemplateUsed(response_all, 'leagues/match_list.html')
        self.assertEqual(len(response_all.context['matches']), 5) # m1, m2, m3, m_upcoming, m_old
        self.assertEqual(response_all.context['active_tab'], 'all')

        # Tes filter tab=upcoming
        response_upcoming = self.client.get(url, {'tab': 'upcoming'})
        self.assertEqual(response_upcoming.status_code, 200)
        self.assertEqual(len(response_upcoming.context['matches']), 1)
        self.assertEqual(response_upcoming.context['matches'][0], self.m_upcoming)
        self.assertEqual(response_upcoming.context['active_tab'], 'upcoming')

        # Tes filter tab=finished
        response_finished = self.client.get(url, {'tab': 'finished'})
        self.assertEqual(response_finished.status_code, 200)
        self.assertEqual(len(response_finished.context['matches']), 4) # m1, m2, m3, m_old
        self.assertEqual(response_finished.context['active_tab'], 'finished')

        # Tes filter team (nama mengandung 'Charlie')
        response_team = self.client.get(url, {'team': 'Charlie'})
        self.assertEqual(response_team.status_code, 200)
        self.assertEqual(len(response_team.context['matches']), 2) # m2(t1 vs t3), m3(t2 vs t3)
        self.assertEqual(response_team.context['team_q'], 'Charlie')

        # Tes filter date range (hanya m_old)
        date_str = self.m_old.date.strftime('%Y-%m-%d')
        response_date = self.client.get(url, {'from': date_str, 'to': date_str})
        self.assertEqual(response_date.status_code, 200)
        self.assertEqual(len(response_date.context['matches']), 1)
        self.assertEqual(response_date.context['matches'][0], self.m_old)
        self.assertEqual(response_date.context['from_q'], date_str)
        self.assertEqual(response_date.context['to_q'], date_str)

    def test_standings_view_and_filters(self):
        """Tes halaman klasemen dengan filter musim."""
        url = reverse('leagues:standings', kwargs={'pk': self.league.pk})

        # Tes tanpa filter (default musim terbaru)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leagues/standings.html')
        self.assertEqual(response.context['selected_season'], '2024/2025')
        self.assertEqual(len(response.context['standings']), 3) # t1, t2, t3
        self.assertCountEqual(response.context['seasons'], ['2023/2024', '2024/2025'])

        # Tes filter musim lama
        response_old = self.client.get(url, {'season': '2023/2024'})
        self.assertEqual(response_old.status_code, 200)
        self.assertEqual(response_old.context['selected_season'], '2023/2024')
        self.assertEqual(len(response_old.context['standings']), 2) # t1, t2

    def test_team_list_view_and_search(self):
        """Tes daftar tim dengan filter pencarian GET (non-AJAX)."""
        url = reverse('leagues:team_list', kwargs={'pk': self.league.pk})

        # Tes tanpa query
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leagues/team_list.html')
        # Harusnya mengembalikan template penuh, bukan partial
        self.assertContains(response, '<h1')
        self.assertEqual(response.context['q'], '')
        # Cek jumlah tim di context (sebelum pagination)
        # Note: ListView context['teams'] biasanya adalah page_obj.object_list
        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj.object_list), 3)

        # Tes dengan query 'Alpha'
        response_q = self.client.get(url, {'q': 'Alpha'})
        self.assertEqual(response_q.status_code, 200)
        self.assertTemplateUsed(response_q, 'leagues/team_list.html')
        self.assertEqual(response_q.context['q'], 'Alpha')
        page_obj_q = response_q.context['page_obj']
        self.assertEqual(len(page_obj_q.object_list), 1)
        self.assertEqual(page_obj_q.object_list[0], self.t1)

    # --- Tes AJAX untuk TeamListView ---
    def test_team_list_view_ajax_search(self):
        """Tes daftar tim dengan filter pencarian GET via AJAX."""
        url = reverse('leagues:team_list', kwargs={'pk': self.league.pk})

        # Tes AJAX tanpa query
        response_ajax = self.client.get(url, **self.ajax_headers)
        self.assertEqual(response_ajax.status_code, 200)
        # Harusnya merender partial template
        self.assertTemplateUsed(response_ajax, 'leagues/_team_list_partial.html')
        # Pastikan tidak ada tag <html> atau <body> dari base.html
        self.assertNotContains(response_ajax, '<html')
        self.assertNotContains(response_ajax, '<body')
        # Cek apakah ada 3 tim di respons
        self.assertContains(response_ajax, self.t1.name)
        self.assertContains(response_ajax, self.t2.name)
        self.assertContains(response_ajax, self.t3.name)

        # Tes AJAX dengan query 'Bravo'
        response_q_ajax = self.client.get(url, {'q': 'Bravo'}, **self.ajax_headers)
        self.assertEqual(response_q_ajax.status_code, 200)
        self.assertTemplateUsed(response_q_ajax, 'leagues/_team_list_partial.html')
        # Hanya ada Bravo Team
        self.assertContains(response_q_ajax, self.t2.name)
        self.assertNotContains(response_q_ajax, self.t1.name)
        self.assertNotContains(response_q_ajax, self.t3.name)

        # Tes AJAX dengan query yang tidak ada hasil
        response_empty_ajax = self.client.get(url, {'q': 'Omega'}, **self.ajax_headers)
        self.assertEqual(response_empty_ajax.status_code, 200)
        self.assertTemplateUsed(response_empty_ajax, 'leagues/_team_list_partial.html')
        self.assertContains(response_empty_ajax, "Tidak ada tim yang ditemukan.") # Cek pesan empty

    def test_team_detail_view(self):
        """Tes halaman detail tim."""
        url = reverse('leagues:team_detail', kwargs={'team_id': self.t1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leagues/team_detail.html')
        self.assertEqual(response.context['team'], self.t1)
        self.assertEqual(response.context['league'], self.league)
        # Cek konteks penting
        self.assertEqual(response.context['selected_season'], '2024/2025')
        self.assertIsNotNone(response.context['standing'])
        self.assertEqual(response.context['standing'].points, 4)
        self.assertEqual(len(response.context['recent_matches']), 2) # m1, m2
        self.assertEqual(response.context['next_match'], self.m_upcoming)

    def test_match_detail_view(self):
        """Tes halaman detail pertandingan."""
        url = reverse('leagues:match_detail', kwargs={'match_id': self.m1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leagues/match_detail.html')
        self.assertEqual(response.context['match'], self.m1)
        self.assertEqual(response.context['league'], self.league)
        # Cek konteks statistik
        self.assertIn('home_stats', response.context)
        self.assertIn('away_stats', response.context)
        self.assertEqual(response.context['home_stats']['Tembakan'], self.m1.home_shots) # Contoh cek satu stat


    # === Tes View Staff-Only (CRUD Match) ===

    # --- Pengujian Permission ---
    # Kita bisa gunakan helper `staff_only_test`
    # Contoh penggunaan untuk match_create GET:
    def test_match_create_view_permissions_get(self):
        """Tes permission GET untuk halaman tambah match."""
        @staff_only_test('leagues:match_create', kwargs={'pk': self.league.pk}, method='get')
        def test_logic(self, response):
            self.assertTemplateUsed(response, 'leagues/match_create.html')
            self.assertIn('form', response.context)
        test_logic(self)

    def test_match_update_view_permissions_get(self):
        """Tes permission GET untuk halaman edit match."""
        @staff_only_test('leagues:match_update', kwargs={'match_id': self.m1.pk}, method='get')
        def test_logic(self, response):
            self.assertTemplateUsed(response, 'leagues/match_update.html')
            self.assertIn('form', response.context)
            self.assertEqual(response.context['object'], self.m1)
        test_logic(self)

    def test_match_delete_view_permissions_get(self):
        """Tes permission GET untuk halaman konfirmasi hapus match."""
        @staff_only_test('leagues:match_delete', kwargs={'match_id': self.m1.pk}, method='get')
        def test_logic(self, response):
            self.assertTemplateUsed(response, 'leagues/match_confirm_delete.html')
            self.assertEqual(response.context['object'], self.m1)
        test_logic(self)

    # --- Pengujian Fungsionalitas CRUD (menggunakan staff_client) ---

    def test_match_create_view_post_valid(self):
        """Tes POST valid ke view tambah match (non-AJAX)."""
        url = reverse('leagues:match_create', kwargs={'pk': self.league.pk})
        post_data = {
            'season': '2025/2026',
            'date': (timezone.now() + datetime.timedelta(days=10)).strftime('%Y-%m-%dT%H:%M'), # Format HTML datetime-local
            'home_team': self.t1.pk,
            'away_team': self.t2.pk,
            'status': Match.Status.SCHEDULED,
            'home_score': '', # Kosongkan untuk scheduled
            'away_score': ''
        }
        initial_match_count = Match.objects.count()

        response = self.staff_client.post(url, post_data, follow=False) # follow=False agar bisa cek redirect

        self.assertEqual(Match.objects.count(), initial_match_count + 1)
        new_match = Match.objects.latest('id')
        self.assertEqual(new_match.season, '2025/2026')
        self.assertEqual(new_match.home_team, self.t1)
        self.assertEqual(new_match.league, self.league) # Cek liga diset otomatis
        # Cek redirect ke detail match baru
        self.assertRedirects(response, reverse('leagues:match_detail', kwargs={'match_id': new_match.pk}))
        # Cek pesan sukses (karena follow=False, cek di request setelah redirect)
        response_redirected = self.staff_client.get(response.url)
        messages = list(get_messages(response_redirected.wsgi_request))
        self.assertTrue(any("berhasil ditambahkan" in str(m) for m in messages))


    def test_match_create_view_post_invalid(self):
        """Tes POST invalid ke view tambah match (non-AJAX)."""
        url = reverse('leagues:match_create', kwargs={'pk': self.league.pk})
        post_data = { # Data tidak lengkap
            'season': '2025/2026',
            'home_team': self.t1.pk,
        }
        initial_match_count = Match.objects.count()
        response = self.staff_client.post(url, post_data)

        self.assertEqual(Match.objects.count(), initial_match_count) # Tidak ada match baru
        self.assertEqual(response.status_code, 200) # Tetap di halaman form
        self.assertTemplateUsed(response, 'leagues/match_create.html')
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors) # Form punya error
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Gagal menyimpan" in str(m) for m in messages))

    # --- Tes AJAX untuk Create ---
    def test_match_create_view_post_ajax_valid(self):
        """Tes POST valid ke view tambah match via AJAX."""
        url = reverse('leagues:match_create', kwargs={'pk': self.league.pk})
        post_data = {
            'season': '2026/2027', # Musim berbeda
            'date': (timezone.now() + datetime.timedelta(days=20)).strftime('%Y-%m-%dT%H:%M'),
            'home_team': self.t1.pk,
            'away_team': self.t3.pk,
            'status': Match.Status.SCHEDULED,
        }
        initial_match_count = Match.objects.count()

        response = self.staff_client.post(url, post_data, **self.ajax_headers)

        self.assertEqual(Match.objects.count(), initial_match_count + 1)
        new_match = Match.objects.latest('id')
        self.assertEqual(response.status_code, 200) # AJAX sukses return 200 OK
        try:
            json_data = response.json()
            self.assertTrue(json_data.get('Ok'))
            self.assertIn("berhasil ditambahkan", json_data.get('message', ''))
            # Cek URL redirect sesuai
            expected_redirect = reverse('leagues:match_detail', kwargs={'match_id': new_match.pk})
            self.assertEqual(json_data.get('redirect_url'), expected_redirect)
        except json.JSONDecodeError:
            self.fail("Response AJAX valid create bukan JSON.")

    def test_match_create_view_post_ajax_invalid(self):
        """Tes POST invalid ke view tambah match via AJAX."""
        url = reverse('leagues:match_create', kwargs={'pk': self.league.pk})
        post_data = {'season': '2025/2026'} # Data tidak lengkap
        initial_match_count = Match.objects.count()

        response = self.staff_client.post(url, post_data, **self.ajax_headers)

        self.assertEqual(Match.objects.count(), initial_match_count) # Tidak ada match baru
        self.assertEqual(response.status_code, 400) # AJAX invalid return 400 Bad Request
        try:
            json_data = response.json()
            self.assertFalse(json_data.get('Ok'))
            self.assertIn('errors', json_data) # Harus ada detail error form
            self.assertIn('date', json_data['errors']) # Contoh: error di field date
        except json.JSONDecodeError:
            self.fail("Response AJAX invalid create bukan JSON.")


    def test_match_update_view_post_valid(self):
        """Tes POST valid ke view update match (non-AJAX)."""
        url = reverse('leagues:match_update', kwargs={'match_id': self.m1.pk})
        post_data = {'home_score': 5, 'away_score': 0, 'status': Match.Status.FINISHED}

        response = self.staff_client.post(url, post_data, follow=False)

        self.m1.refresh_from_db()
        self.assertEqual(self.m1.home_score, 5)
        self.assertEqual(self.m1.away_score, 0)
        self.assertRedirects(response, reverse('leagues:match_detail', kwargs={'match_id': self.m1.pk}))
        # Cek pesan
        response_redirected = self.staff_client.get(response.url)
        messages = list(get_messages(response_redirected.wsgi_request))
        self.assertTrue(any("berhasil diperbarui" in str(m) for m in messages))

    def test_match_update_view_post_invalid(self):
        """Tes POST invalid ke view update match (non-AJAX)."""
        url = reverse('leagues:match_update', kwargs={'match_id': self.m1.pk})
        post_data = {'home_score': -10, 'away_score': 0, 'status': Match.Status.FINISHED} # Skor invalid
        original_score = self.m1.home_score

        response = self.staff_client.post(url, post_data)

        self.m1.refresh_from_db()
        self.assertEqual(self.m1.home_score, original_score) # Skor tidak berubah
        self.assertEqual(response.status_code, 200) # Tetap di halaman form
        self.assertTemplateUsed(response, 'leagues/match_update.html')
        self.assertTrue(response.context['form'].errors)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Gagal menyimpan" in str(m) for m in messages))

    # --- Tes AJAX untuk Update (hanya tes respons invalid, valid mirip create) ---
    def test_match_update_view_post_ajax_invalid(self):
        """Tes POST invalid ke view update match via AJAX."""
        url = reverse('leagues:match_update', kwargs={'match_id': self.m1.pk})
        post_data = {'home_score': -5} # Skor invalid
        original_score = self.m1.home_score

        response = self.staff_client.post(url, post_data, **self.ajax_headers)

        self.m1.refresh_from_db()
        self.assertEqual(self.m1.home_score, original_score) # Skor tidak berubah
        self.assertEqual(response.status_code, 400) # AJAX invalid return 400
        try:
            json_data = response.json()
            self.assertFalse(json_data.get('Ok'))
            self.assertIn('errors', json_data)
            self.assertIn('home_score', json_data['errors']) # Error di field home_score
        except json.JSONDecodeError:
            self.fail("Response AJAX invalid update bukan JSON.")


    def test_match_delete_view_post_valid(self):
        """Tes POST valid ke view delete match (non-AJAX)."""
        match_to_delete = Match.objects.create(
            league=self.league, season="2025/2026", date=timezone.now(),
            home_team=self.t1, away_team=self.t2, status=Match.Status.SCHEDULED
        )
        match_pk = match_to_delete.pk
        url = reverse('leagues:match_delete', kwargs={'match_id': match_pk})
        initial_match_count = Match.objects.count()

        response = self.staff_client.post(url, follow=False)

        self.assertEqual(Match.objects.count(), initial_match_count - 1)
        with self.assertRaises(Match.DoesNotExist):
            Match.objects.get(pk=match_pk)
        # Redirect ke match list
        self.assertRedirects(response, reverse('leagues:match_list', kwargs={'pk': self.league.pk}))
        # Cek pesan
        response_redirected = self.staff_client.get(response.url)
        messages = list(get_messages(response_redirected.wsgi_request))
        self.assertTrue(any("berhasil dihapus" in str(m) for m in messages))

    # --- Tes AJAX untuk Delete ---
    def test_match_delete_view_post_ajax_valid(self):
        """Tes POST valid ke view delete match via AJAX."""
        match_to_delete = Match.objects.create(
            league=self.league, season="2027/2028", date=timezone.now(),
            home_team=self.t1, away_team=self.t3, status=Match.Status.SCHEDULED
        )
        match_pk = match_to_delete.pk
        url = reverse('leagues:match_delete', kwargs={'match_id': match_pk})
        initial_match_count = Match.objects.count()

        response = self.staff_client.post(url, **self.ajax_headers)

        self.assertEqual(Match.objects.count(), initial_match_count - 1)
        with self.assertRaises(Match.DoesNotExist):
            Match.objects.get(pk=match_pk)

        self.assertEqual(response.status_code, 200) # AJAX sukses return 200 OK
        try:
            json_data = response.json()
            self.assertTrue(json_data.get('Ok'))
            self.assertIn("berhasil dihapus", json_data.get('message', ''))
            # Cek URL redirect sesuai
            expected_redirect = reverse('leagues:match_list', kwargs={'pk': self.league.pk})
            self.assertEqual(json_data.get('redirect_url'), expected_redirect)
        except json.JSONDecodeError:
            self.fail("Response AJAX valid delete bukan JSON.")

    def test_match_delete_view_post_ajax_not_found(self):
        """Tes POST delete match via AJAX untuk ID yang tidak ada."""
        non_existent_pk = 99999
        url = reverse('leagues:match_delete', kwargs={'match_id': non_existent_pk})
        initial_match_count = Match.objects.count()

        response = self.staff_client.post(url, **self.ajax_headers)

        self.assertEqual(Match.objects.count(), initial_match_count) # Jumlah tidak berubah
        # DeleteView biasanya return 404 jika object tidak ditemukan saat POST
        # Modifikasi di view kita return 500 dengan JSON error
        self.assertEqual(response.status_code, 500)
        try:
            json_data = response.json()
            self.assertFalse(json_data.get('Ok'))
            self.assertIn("Gagal menghapus", json_data.get('message', '')) # Cek pesan error dari view
        except json.JSONDecodeError:
             self.fail(f"Response AJAX delete not found bukan JSON atau status bukan 500.")


class ViewEmptyStateTests(TestCase):
    """Tes view saat tidak ada data (mis. liga baru dibuat)."""
    @classmethod
    def setUpTestData(cls):
        cls.empty_league = League.objects.create(name="Empty League")
        cls.empty_team = Team.objects.create(league=cls.empty_league, name="Empty Team")
        cls.client = Client() # Client anonim cukup

    def test_league_dashboard_empty_state(self):
        """Tes dashboard liga kosong (views.py baris 63, 69)."""
        url = reverse('leagues:league_dashboard', kwargs={'pk': self.empty_league.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leagues/league_dashboard.html')
        self.assertEqual(response.context['league'], self.empty_league)
        # Konteks harus kosong atau None
        self.assertIsNone(response.context['latest_season'])
        self.assertEqual(len(response.context['standings']), 0)
        self.assertEqual(len(response.context['finished_recent']), 0)
        self.assertEqual(len(response.context['upcoming']), 0)
        self.assertContains(response, "Belum ditemukan pertandingan") # Cek pesan empty state

    def test_standings_view_empty_state(self):
        """Tes halaman klasemen kosong (views.py baris 144, 156)."""
        url = reverse('leagues:standings', kwargs={'pk': self.empty_league.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leagues/standings.html')
        self.assertEqual(response.context['league'], self.empty_league)
        # Konteks harus kosong
        self.assertEqual(response.context['seasons'], [])
        self.assertIsNone(response.context['selected_season'])
        self.assertEqual(len(response.context['standings']), 0)
        self.assertContains(response, "Belum ada data klasemen") # Cek pesan empty state

    def test_team_list_view_empty_state(self):
        """Tes halaman daftar tim kosong (non-AJAX)."""
        # Hapus tim yang dibuat di setUpTestData
        Team.objects.filter(league=self.empty_league).delete()
        url = reverse('leagues:team_list', kwargs={'pk': self.empty_league.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leagues/team_list.html')
        page_obj = response.context['page_obj']
        self.assertEqual(len(page_obj.object_list), 0)
        self.assertContains(response, "Tidak ada tim yang ditemukan.") # Cek pesan empty

        # Kembalikan tim untuk tes lain
        self.empty_team = Team.objects.create(league=self.empty_league, name="Empty Team")

    def test_team_detail_view_empty_state(self):
        """Tes detail tim tanpa match/standing (views.py baris 195, 205, 213, 222)."""
        url = reverse('leagues:team_detail', kwargs={'team_id': self.empty_team.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leagues/team_detail.html')
        self.assertEqual(response.context['team'], self.empty_team)
        self.assertEqual(response.context['league'], self.empty_league)
        # Konteks harus kosong atau None
        self.assertEqual(response.context['seasons'], [])
        self.assertIsNone(response.context['selected_season'])
        self.assertIsNone(response.context['standing'])
        self.assertEqual(len(response.context['recent_matches']), 0)
        self.assertIsNone(response.context['next_match'])
        self.assertContains(response, "Belum ada data klasemen") # Cek pesan empty


class AdminViewTests(TestCase):
    """Tes logic permission dan action di admin.py."""
    @classmethod
    def setUpTestData(cls):
        cls.data = create_test_data()
        cls.superuser = cls.data['superuser']
        cls.staff_user = cls.data['staff']
        # Pastikan user ini adalah staff tapi BUKAN superuser
        cls.staff_user.is_staff = True
        cls.staff_user.is_superuser = False
        cls.staff_user.save()

        cls.league = cls.data['league']
        cls.team = cls.data['t1']
        cls.match = cls.data['m1']
        # Standing mungkin sudah dibuat oleh create_test_data -> recompute_...
        # Jika belum, buat di sini
        if not Standing.objects.filter(league=cls.league).exists():
             Standing.objects.create(
                 league=cls.league, season="2024/2025", team=cls.team, points=3
             )
        cls.standing = Standing.objects.first()

        cls.factory = RequestFactory()
        # Perlu setup admin site minimal agar reverse('admin:...') berfungsi
        cls.admin_site = admin.AdminSite()

    def test_admin_actions_as_superuser(self):
        """Superuser harus selalu melihat action 'delete_selected'."""
        self.client.login(username='admin', password='password123')
        # Daftarkan model admin ke site tes jika belum
        # if not isinstance(admin.site._registry.get(League), LeagueAdmin): # Cek jika sudah terdaftar global
        #     self.admin_site.register(League, LeagueAdmin)
        #     self.admin_site.register(Team, TeamAdmin)
        #     self.admin_site.register(Match, MatchAdmin)
        #     self.admin_site.register(Standing, StandingAdmin)

        urls = {
            'league': reverse('admin:leagues_league_changelist'),
            'team': reverse('admin:leagues_team_changelist'),
            'match': reverse('admin:leagues_match_changelist'),
            'standing': reverse('admin:leagues_standing_changelist'),
        }

        for name, url in urls.items():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Failed for {name}")
            # Di Django 4+, actions ada di context['actions_selection_counter'] > 0
            # Cara lebih robust: cek HTML respons mengandung 'name="action"' dan 'value="delete_selected"'
            self.assertContains(response, 'name="action"')
            self.assertContains(response, 'value="delete_selected"')

    def test_admin_actions_as_staff_no_delete_perm(self):
        """Tes staff user tanpa izin delete: action 'delete_selected' hilang."""
        # admin.py baris 11-14, 23-26, 38-41, 57-60: `if not request.user.has_perm(...)`
        self.client.login(username='staffuser', password='password123')
        # Pastikan staff ini TIDAK punya izin delete
        self.staff_user.user_permissions.clear()

        urls = {
            'league': reverse('admin:leagues_league_changelist'),
            'team': reverse('admin:leagues_team_changelist'),
            'match': reverse('admin:leagues_match_changelist'),
            'standing': reverse('admin:leagues_standing_changelist'),
        }

        for name, url in urls.items():
            # Beri izin view saja agar bisa buka changelist
            # Gunakan format app_label.codename
            view_perm_codename = f'view_{name}'
            try:
                view_perm = Permission.objects.get(content_type__app_label='leagues', codename=view_perm_codename)
                self.staff_user.user_permissions.add(view_perm)
            except Permission.DoesNotExist:
                 self.fail(f"Permission leagues.{view_perm_codename} not found. Did you run migrations?")

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Failed for {name}")

            # Aksi 'delete_selected' harusnya TIDAK ADA di HTML respons
            self.assertNotContains(response, 'value="delete_selected"')

            # Bersihkan permission untuk tes model berikutnya
            self.staff_user.user_permissions.clear()

    def test_standing_admin_custom_permissions(self):
        """Tes has_add, has_change, has_delete di StandingAdmin."""
        # admin.py baris 51, 53, 55
        admin_model = StandingAdmin(Standing, self.admin_site)

        # Buat mock request dengan staff_user
        request = self.factory.get(reverse('admin:leagues_standing_changelist'))
        request.user = self.staff_user

        # 1. Tes tanpa izin
        self.staff_user.user_permissions.clear() # Pastikan bersih
        self.assertFalse(admin_model.has_add_permission(request))
        self.assertFalse(admin_model.has_change_permission(request, obj=self.standing))
        self.assertFalse(admin_model.has_delete_permission(request, obj=self.standing))

        # Helper untuk mendapatkan permission
        def get_perm(codename):
            try:
                return Permission.objects.get(content_type__app_label='leagues', codename=codename)
            except Permission.DoesNotExist:
                 self.fail(f"Permission leagues.{codename} not found.")

        # 2. Tes dengan izin add
        self.staff_user.user_permissions.add(get_perm('add_standing'))
        self.assertTrue(admin_model.has_add_permission(request))
        self.assertFalse(admin_model.has_change_permission(request, obj=self.standing)) # Change belum
        self.staff_user.user_permissions.clear()

        # 3. Tes dengan izin change
        self.staff_user.user_permissions.add(get_perm('change_standing'))
        self.assertFalse(admin_model.has_add_permission(request)) # Add belum
        self.assertTrue(admin_model.has_change_permission(request, obj=self.standing))
        self.staff_user.user_permissions.clear()

        # 4. Tes dengan izin delete
        self.staff_user.user_permissions.add(get_perm('delete_standing'))
        self.assertFalse(admin_model.has_add_permission(request)) # Add belum
        self.assertFalse(admin_model.has_change_permission(request, obj=self.standing)) # Change belum
        self.assertTrue(admin_model.has_delete_permission(request, obj=self.standing))
        self.staff_user.user_permissions.clear()

class ManagementCommandTests(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        # Buat data minimal untuk tes commands
        cls.league = League.objects.create(name="Import League")
        Team.objects.create(league=cls.league, name="CSV Team A")
        Team.objects.create(league=cls.league, name="CSV Team B")

    def test_init_roles_command(self):
        """Tes command init_roles."""
        # Gunakan StringIO untuk menangkap output
        out = StringIO()
        # Panggil command
        call_command('init_roles', stdout=out)
        
        # Periksa apakah grup telah dibuat
        self.assertTrue(Group.objects.filter(name="Registered User").exists())
        self.assertTrue(Group.objects.filter(name="Editor").exists())
        self.assertTrue(Group.objects.filter(name="Administrator").exists())
        
        # Periksa pesan sukses di output
        self.assertIn("Roles initialized", out.getvalue())

    def test_import_matches_command(self):
        """Tes command import_matches dengan file CSV temporer."""
        
        # 1. Buat file CSV temporer
        csv_content = (
            "season,date,home_team,away_team,goal_home_ft,goal_away_ft\n"
            "2024/2025,2025-01-01,CSV Team A,CSV Team B,2,1\n"
            "2024/2025,2025-01-08,CSV Team B,CSV Team A,0,0\n"
        )
        
        # tempfile.NamedTemporaryFile sering bermasalah di Windows,
        # jadi kita buat manual saja:
        temp_dir = tempfile.gettempdir()
        temp_csv_path = os.path.join(temp_dir, "test_import.csv")
        
        try:
            with open(temp_csv_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)

            out = StringIO()
            
            # 2. Panggil command dengan menunjuk ke file CSV temporer
            call_command(
                'import_matches',
                '--csv', temp_csv_path,
                '--league-name', self.league.name, # Pastikan liga sudah ada
                stdout=out
            )
            
            # 3. Periksa hasilnya
            # Dua match harus dibuat
            self.assertEqual(Match.objects.filter(league=self.league).count(), 2)
            # Standings harus dihitung (2 tim)
            self.assertEqual(Standing.objects.filter(league=self.league).count(), 2)
            
            # Periksa pesan sukses
            output = out.getvalue()
            self.assertIn("Imported: 2, Skipped duplicates: 0", output)
            self.assertIn("Standings recomputed.", output)

        finally:
            # 4. Hapus file temporer
            if os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)

    def test_import_matches_command_file_not_found(self):
        """Tes command import_matches jika file tidak ada."""
        
        # Panggil command dengan path yang pasti tidak ada
        with self.assertRaises(CommandError) as cm:
            call_command('import_matches', '--csv', 'path/yang/salah.csv')
        
        self.assertIn("File not found", str(cm.exception))

    def test_import_matches_command_missing_columns(self):
        """Tes command import_matches jika kolom CSV kurang."""
        
        csv_content = "season,date,home_team\n" # Kurang away_team, dll.
        temp_dir = tempfile.gettempdir()
        temp_csv_path = os.path.join(temp_dir, "test_missing_col.csv")

        try:
            with open(temp_csv_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)

            with self.assertRaises(CommandError) as cm:
                call_command('import_matches', '--csv', temp_csv_path)
            
            self.assertIn("CSV missing required columns", str(cm.exception))

        finally:
            if os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)