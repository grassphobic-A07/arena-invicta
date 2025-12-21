from django.utils import timezone
from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404, redirect, render
from .models import League, Match, Standing, Team
from django.views.generic import TemplateView
from django.db.models import Q, F
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .permissions import is_content_staff
from django.urls import reverse_lazy
from django.views.generic import UpdateView, DeleteView, CreateView
from .forms import MatchUpdateForm, MatchCreateForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect 
from django.http import HttpResponse
from django.core import serializers
from .models import League, Team, Match, Standing
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime

def _is_ajax(request):
    """ Cek apakah request datang dari AJAX """
    return request.headers.get("x-requested-with") == "XMLHttpRequest"

def league_redirect_view(request):
    """
    Mengalihkan ke dashboard liga pertama yang ditemukan.
    """
    league = League.objects.first() # Ambil liga pertama
    if league:
        # Jika liga ada, alihkan ke dashboard-nya
        return redirect('leagues:league_dashboard', pk=league.pk)
    
    # Fallback jika tidak ada liga sama sekali (mis. database kosong)
    # Kita kembalikan ke halaman utama 'accounts:home'
    messages.warning(request, "Belum ada data liga untuk ditampilkan.")
    return redirect('accounts:home')

class LeagueDashboardView(DetailView):
    model = League
    template_name = "leagues/league_dashboard.html"
    context_object_name = "league"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        league = self.object

        # season terbaru: ambil distinct season dari Match, pilih paling "besar" secara leksikografis
        seasons = (
            Match.objects.filter(league=league)
            .values_list("season", flat=True)
            .distinct()
        )
        latest_season = None
        if seasons:
            latest_season = sorted(seasons)[-1]  # "10/11","11/12",... -> cukup untuk MVP
        ctx["latest_season"] = latest_season

        # standings untuk season terbaru
        standings = []
        if latest_season:
            standings = (
                Standing.objects.filter(league=league, season=latest_season)
                .select_related("team")
            )
        ctx["standings"] = standings

        # pertandingan terbaru selesai (5)
        finished = (
            Match.objects.filter(league=league, status=Match.Status.FINISHED)
            .select_related("home_team", "away_team")
            .order_by("-date")[:5]
        )
        ctx["finished_recent"] = finished

        # pertandingan akan datang (5) – bisa kosong jika dataset FT semua
        now = timezone.now()  # USE_TZ=True → ini UTC-aware
        upcoming = (
            Match.objects.filter(league=league, date__gt=now)
            .select_related("home_team", "away_team")
            .order_by("date")[:5]
        )
        ctx["upcoming"] = upcoming

        return ctx

class MatchListView(ListView):
    model = Match
    template_name = "leagues/match_list.html"
    context_object_name = "matches"
    paginate_by = 20

    def get_queryset(self):
        league = League.objects.get(pk=self.kwargs["pk"])
        qs = Match.objects.filter(league=league).select_related("home_team", "away_team").order_by("-date")

        # tab: ?tab=upcoming|finished|all (default: all)
        tab = self.request.GET.get("tab", "all")
        now = timezone.now()
        if tab == "upcoming":
            qs = qs.filter(date__gt=now).order_by("date")
        elif tab == "finished":
            qs = qs.filter(status=Match.Status.FINISHED)

        # filter tambahan (opsional)
        team = self.request.GET.get("team")
        if team:
            qs = qs.filter(Q(home_team__name__icontains=team) | Q(away_team__name__icontains=team))

        date_from = self.request.GET.get("from")
        date_to = self.request.GET.get("to")
        if date_from:
            qs = qs.filter(date__date__gte=date_from)  # format YYYY-MM-DD
        if date_to:
            qs = qs.filter(date__date__lte=date_to)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        league = League.objects.get(pk=self.kwargs["pk"])
        ctx["league"] = league
        ctx["active_tab"] = self.request.GET.get("tab", "all")
        ctx["team_q"] = self.request.GET.get("team", "")
        ctx["from_q"] = self.request.GET.get("from", "")
        ctx["to_q"]   = self.request.GET.get("to", "")
        return ctx
    
class StandingsView(TemplateView):
    template_name = "leagues/standings.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        league = League.objects.get(pk=self.kwargs["pk"])
        ctx["league"] = league

        # daftar musim yang tersedia dari data Match
        seasons = list(
            Match.objects.filter(league=league)
            .values_list("season", flat=True)
            .distinct()
        )
        seasons.sort()  # "10/11","11/12", ...

        # pilih musim dari query ?season=..., default: musim terakhir
        selected = self.request.GET.get("season") or (seasons[-1] if seasons else None)
        ctx["seasons"] = seasons
        ctx["selected_season"] = selected

        standings = []
        if selected:
            standings = (
                Standing.objects.filter(league=league, season=selected)
                .select_related("team")
            )
        ctx["standings"] = standings
        return ctx
    
class TeamListView(ListView):
    template_name = "leagues/team_list.html"
    context_object_name = "teams"
    paginate_by = 30 # <-- Pagination mungkin perlu penyesuaian untuk AJAX nanti

    def get_queryset(self):
        league = League.objects.get(pk=self.kwargs["pk"])
        qs = Team.objects.filter(league=league).order_by("name")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["league"] = League.objects.get(pk=self.kwargs["pk"])
        ctx["q"] = self.request.GET.get("q", "")
        return ctx

    # --- TAMBAHKAN METODE INI (untuk Contoh 2: Filter GET AJAX) ---
    def render_to_response(self, context, **response_kwargs):
        """
        Override render_to_response.
        Jika ini request AJAX, render partial template.
        Jika tidak, render template penuh (standar).
        """
        if _is_ajax(self.request):
            # Jika AJAX, kirim HANYA bagian daftar tim
            return render(
                self.request,
                "leagues/_team_list_partial.html", # Nama template partial
                context
            )
        
        # Jika request standar (non-AJAX), lakukan render normal
        return super().render_to_response(context, **response_kwargs)

class TeamDetailView(TemplateView):
    template_name = "leagues/team_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        team = Team.objects.select_related("league").get(pk=self.kwargs["team_id"])
        league = team.league
        ctx["team"] = team
        ctx["league"] = league

        # daftar musim untuk navigasi
        seasons = list(
            Match.objects.filter(Q(home_team=team) | Q(away_team=team))
            .values_list("season", flat=True).distinct()
        )
        seasons.sort()
        selected = self.request.GET.get("season") or (seasons[-1] if seasons else None)
        ctx["seasons"] = seasons
        ctx["selected_season"] = selected

        # posisi di klasemen musim terpilih
        standing = None
        if selected:
            standing = (Standing.objects
                        .select_related("team")
                        .filter(league=league, season=selected, team=team)
                        .first())
        ctx["standing"] = standing

        # 5 laga terakhir (FINISHED) untuk musim terpilih
        recent = (Match.objects
                  .filter(league=league, season=selected, status=Match.Status.FINISHED)
                  .filter(Q(home_team=team) | Q(away_team=team))
                  .select_related("home_team","away_team")
                  .order_by("-date")[:5]) if selected else []
        ctx["recent_matches"] = recent

        # laga mendatang terdekat (jika ada)
        from django.utils import timezone
        now = timezone.now()
        upcoming = (Match.objects
                    .filter(league=league, season=selected, date__gt=now)
                    .filter(Q(home_team=team) | Q(away_team=team))
                    .select_related("home_team","away_team")
                    .order_by("date")[:1]) if selected else []
        ctx["next_match"] = upcoming[0] if upcoming else None

        return ctx
    
class MatchDetailView(TemplateView):
    template_name = "leagues/match_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        m = get_object_or_404(
            Match.objects.select_related("league","home_team","away_team"),
            pk=self.kwargs["match_id"]
        )
        ctx["match"] = m
        ctx["league"] = m.league

        # siapkan blok statistik agar rapi di template
        ctx["home_stats"] = {
            "Tembakan": m.home_shots,
            "Tepat Sasaran": m.home_shots_on_target,
            "Penguasaan Bola (%)": m.home_possession,
            "Umpan": m.home_passes,
            "Corner": m.home_corners,
            "Offside": m.home_offsides,
            "Pelanggaran": m.home_fouls_conceded,
            "Tackle": m.home_tackles,
            "Clearance": m.home_clearances,
            "Kartu Kuning": m.home_yellow_cards,
            "Kartu Merah": m.home_red_cards,
            "Touches": m.home_touches,
        }
        ctx["away_stats"] = {
            "Tembakan": m.away_shots,
            "Tepat Sasaran": m.away_shots_on_target,
            "Penguasaan Bola (%)": m.away_possession,
            "Umpan": m.away_passes,
            "Corner": m.away_corners,
            "Offside": m.away_offsides,
            "Pelanggaran": m.away_fouls_conceded,
            "Tackle": m.away_tackles,
            "Clearance": m.away_clearances,
            "Kartu Kuning": m.away_yellow_cards,
            "Kartu Merah": m.away_red_cards,
            "Touches": m.away_touches,
        }
        return ctx
    
class ContentStaffOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return is_content_staff(self.request.user)
    
# Catatan: Ada dua definisi MatchUpdateView di kode Anda, saya akan gabungkan
# dan pastikan AJAX bisa diterapkan (meskipun contoh ini fokus pada Delete).
class MatchUpdateView(ContentStaffOnlyMixin, UpdateView):
    model = Match
    form_class = MatchUpdateForm # Menggunakan form class
    # fields = ["home_score", "away_score", "status"] # Tidak perlu jika pakai form_class
    template_name = "leagues/match_update.html"
    pk_url_kwarg = "match_id"

    def form_valid(self, form):
        resp = super().form_valid(form)
        # Jika AJAX, mungkin ingin return JsonResponse, tapi redirect saja cukup
        messages.success(self.request, "Skor pertandingan berhasil diperbarui.")
        return resp

    def form_invalid(self, form):
        # Jika AJAX, return JsonResponse error
        if _is_ajax(self.request):
             return JsonResponse({"Ok": False, "errors": form.errors}, status=400)
        
        messages.error(self.request, "Gagal menyimpan. Periksa input Anda.")
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("leagues:match_detail", kwargs={"match_id": self.object.pk})
    
class MatchDeleteView(ContentStaffOnlyMixin, DeleteView):
    model = Match
    pk_url_kwarg = "match_id"
    template_name = "leagues/match_confirm_delete.html"

    def get_success_url(self):
        # selesai hapus → balik ke daftar pertandingan liga terkait
        league = self.object.league
        return reverse_lazy("leagues:match_list", kwargs={"pk": league.pk})

    # --- MODIFIKASI METODE POST UNTUK AJAX ---
    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            success_url = self.get_success_url()
            league_pk = self.object.league.pk # Simpan pk sebelum dihapus
            self.object.delete()

            if _is_ajax(request):
                return JsonResponse({
                    "Ok": True,
                    "redirect_url": success_url, # Beri tahu JS ke mana harus redirect
                    "message": "Pertandingan berhasil dihapus." # Pesan untuk toast
                })
            
            # Fallback untuk non-AJAX (jika JS gagal load)
            messages.success(request, "Pertandingan berhasil dihapus.")
            # Redirect seperti biasa
            return HttpResponseRedirect(success_url) 
            
        except Exception as e:
            # Tangani error
            error_message = f"Gagal menghapus pertandingan: {e}"
            if _is_ajax(request):
                # Kirim error sebagai JSON jika AJAX
                return JsonResponse({"Ok": False, "message": error_message}, status=500)
            
            # Tampilkan pesan error standar jika non-AJAX
            messages.error(request, error_message)
            # Kembali ke halaman konfirmasi jika gagal
            # Perlu get_object lagi atau redirect ke detail match jika masih ada
            try:
                # Coba redirect ke detail jika object masih ada (jarang terjadi tapi aman)
                detail_url = reverse_lazy("leagues:match_detail", kwargs={"match_id": self.kwargs["match_id"]})
                return HttpResponseRedirect(detail_url)
            except:
                # Jika object sudah terlanjur hilang atau error lain, kembali ke list
                list_url = reverse_lazy("leagues:match_list", kwargs={"pk": league_pk if 'league_pk' in locals() else 1}) # Ganti 1 dengan fallback jika perlu
                return HttpResponseRedirect(list_url)

class MatchCreateView(ContentStaffOnlyMixin, CreateView):
    model = Match
    form_class = MatchCreateForm
    template_name = "leagues/match_create.html"

    def dispatch(self, request, *args, **kwargs):
        # simpan liga terpilih dari URL
        self.league = get_object_or_404(League, pk=self.kwargs["pk"]) # Lebih aman pakai get_object_or_404
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["league"] = self.league  # untuk filter queryset tim
        return kwargs

    def form_valid(self, form):
        # obj = form.save(commit=False) # super().form_valid sudah melakukan ini
        # obj.league = self.league  # pastikan match masuk ke liga ini
        # obj.save()
        form.instance.league = self.league # Set liga sebelum super().form_valid menyimpan
        response = super().form_valid(form) # Simpan object dan dapatkan redirect response
        
        # Jika AJAX, kita override response menjadi JSON
        if _is_ajax(self.request):
            return JsonResponse({
                "Ok": True,
                "redirect_url": self.get_success_url(),
                "message": "Pertandingan berhasil ditambahkan."
            })
        
        messages.success(self.request, "Pertandingan berhasil ditambahkan.") # Tambahkan pesan sukses untuk non-AJAX
        return response # Return redirect response standar

    def form_invalid(self, form):
         # Jika AJAX, return JsonResponse error
        if _is_ajax(self.request):
             return JsonResponse({"Ok": False, "errors": form.errors}, status=400)
        
        messages.error(self.request, "Gagal menyimpan. Periksa input Anda.") # Tambahkan pesan error untuk non-AJAX
        return super().form_invalid(form) # Render ulang form dengan error

    def get_success_url(self):
        # Redirect ke detail match yang baru dibuat
        return reverse_lazy("leagues:match_detail", kwargs={"match_id": self.object.pk})
    
def show_leagues_json(request):
    data = League.objects.all()
    return HttpResponse(serializers.serialize("json", data), content_type="application/json")

def show_teams_json(request):
    data = Team.objects.all()
    return HttpResponse(serializers.serialize("json", data), content_type="application/json")

def show_matches_json(request):
    league = League.objects.first()
    if not league:
        return HttpResponse("[]", content_type="application/json")
    
    data = Match.objects.filter(league=league).order_by('-date')
    return HttpResponse(serializers.serialize("json", data), content_type="application/json")

def show_standings_json(request):
    data = Standing.objects.all()
    return HttpResponse(serializers.serialize("json", data), content_type="application/json")

def show_standings_json(request):
    league = League.objects.first()
    data = Standing.objects.filter(league=league).order_by('-points', '-gd', '-gf')
    return HttpResponse(serializers.serialize("json", data), content_type="application/json")

@csrf_exempt
def create_team_flutter(request):
    # 1. Cek apakah Method POST
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    
    # 2. Cek apakah User sudah Login
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Anda harus login terlebih dahulu."}, status=401)

    # 3. Cek apakah User adalah Admin/Staff
    if not request.user.is_staff: # is_staff True untuk admin & staff
        return JsonResponse({"status": "error", "message": "Hanya admin yang boleh melakukan ini!"}, status=403)

    # --- JIKA LOLOS PENGECEKAN DI ATAS, BARU JALANKAN LOGIKA SIMPAN ---
    try:
        data = json.loads(request.body)
        
        # Ambil Liga pertama sebagai default (Logic sementara)
        league = League.objects.first()
        if not league:
            league = League.objects.create(name="Default League", country="Indonesia")

        new_team = Team.objects.create(
            league=league,
            name=data.get("name"),
            short_name=data.get("short_name"),
        )
        new_team.save()

        return JsonResponse({"status": "success", "message": "Tim berhasil dibuat!"}, status=200)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


    
@csrf_exempt
def create_standing_flutter(request):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    
    # Pastikan user login (bisa disesuaikan jika ingin memperbolehkan guest sementara waktu)
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Anda harus login terlebih dahulu."}, status=401)

    try:
        data = json.loads(request.body)
        
        # Ambil Liga Default
        league = League.objects.first()
        if not league:
            return JsonResponse({"status": "error", "message": "Data liga tidak ditemukan."}, status=404)

        # Cari Team
        team_id = int(data.get("team_id"))
        team = Team.objects.get(pk=team_id)
        season = data.get("season", "23/24") # Default season jika kosong

        # VALIDASI: Cek apakah tim sudah ada di musim ini?
        if Standing.objects.filter(league=league, team=team, season=season).exists():
            return JsonResponse({"status": "error", "message": f"Tim {team.name} sudah ada di klasemen musim {season}."}, status=400)

        # Ambil statistik dasar dari input
        win = int(data.get("win", 0))
        draw = int(data.get("draw", 0))
        loss = int(data.get("loss", 0))
        gf = int(data.get("gf", 0))
        ga = int(data.get("ga", 0))

        # LOGIKA OTOMATIS (Backend Calculation)
        played = win + draw + loss
        points = (win * 3) + (draw * 1)
        gd = gf - ga

        new_standing = Standing.objects.create(
            league=league,
            team=team,
            season=season,
            played=played,
            win=win,
            draw=draw,
            loss=loss,
            gf=gf,
            ga=ga,
            gd=gd,
            points=points,
        )
        new_standing.save()

        return JsonResponse({"status": "success", "message": "Klasemen berhasil disimpan!"}, status=200)

    except Team.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Tim tidak ditemukan."}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
@csrf_exempt
def edit_standing_flutter(request, id):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Login required"}, status=401)

    try:
        standing = Standing.objects.get(pk=id)
        data = json.loads(request.body)

        # Update data dasar
        # Kita gunakan 'getattr' atau logika sederhana untuk mengambil nilai baru atau mempertahankan nilai lama
        standing.win = int(data.get("win", standing.win))
        standing.draw = int(data.get("draw", standing.draw))
        standing.loss = int(data.get("loss", standing.loss))
        standing.gf = int(data.get("gf", standing.gf))
        standing.ga = int(data.get("ga", standing.ga))
        
        standing.played = standing.win + standing.draw + standing.loss
        standing.points = (standing.win * 3) + (standing.draw * 1)
        standing.gd = standing.gf - standing.ga
        
        # Season biasanya tidak diubah saat edit statistik, tapi bisa ditambahkan jika perlu
        # standing.season = data.get("season", standing.season)

        standing.save()

        return JsonResponse({"status": "success", "message": "Data berhasil diperbarui!"}, status=200)

    except Standing.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Data tidak ditemukan."}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def delete_standing_flutter(request, id):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    
    # Cek Admin
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"status": "error", "message": "Hanya admin yang boleh melakukan ini!"}, status=403)

    try:
        standing = Standing.objects.get(pk=id)
        standing.delete()
        return JsonResponse({"status": "success", "message": "Data berhasil dihapus!"}, status=200)

    except Standing.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Data tidak ditemukan."}, status=404)

@csrf_exempt
def create_match_flutter(request):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"status": "error", "message": "Hanya admin yang boleh melakukan ini!"}, status=403)

    try:
        data = json.loads(request.body)
        league = League.objects.first()
        
        # Ambil Tim
        home_team_id = int(data.get("home_team_id"))
        away_team_id = int(data.get("away_team_id"))
        
        # Validasi: Tim kandang tidak boleh sama dengan tim tandang
        if home_team_id == away_team_id:
             return JsonResponse({"status": "error", "message": "Tim kandang dan tandang tidak boleh sama."}, status=400)

        home_team = Team.objects.get(pk=home_team_id)
        away_team = Team.objects.get(pk=away_team_id)
        
        # Parsing Tanggal (Format ISO 8601 dari Flutter)
        date_str = data.get("date") # Contoh: "2023-12-31T15:30:00"
        match_date = parse_datetime(date_str)
        if not match_date:
            return JsonResponse({"status": "error", "message": "Format tanggal tidak valid."}, status=400)

        # Buat Match Baru
        new_match = Match.objects.create(
            league=league,
            season=data.get("season", "23/24"),
            date=match_date,
            home_team=home_team,
            away_team=away_team,
            home_score=int(data.get("home_score", 0)),
            away_score=int(data.get("away_score", 0)),
            status="FINISHED" if data.get("is_finished") else "SCHEDULED" 
        )
        new_match.save()

        return JsonResponse({"status": "success", "message": "Pertandingan berhasil dibuat!"}, status=200)

    except Team.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Tim tidak ditemukan."}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
@csrf_exempt
def edit_match_flutter(request, id):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    
    # Pastikan user adalah admin/staff
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"status": "error", "message": "Hanya admin yang boleh melakukan ini!"}, status=403)

    try:
        match_obj = Match.objects.get(pk=id)
        data = json.loads(request.body)

        # 1. Update Tim (Jika ada perubahan)
        if "home_team_id" in data:
            match_obj.home_team = Team.objects.get(pk=int(data["home_team_id"]))
        
        if "away_team_id" in data:
            match_obj.away_team = Team.objects.get(pk=int(data["away_team_id"]))

        # Validasi: Tim tidak boleh sama
        if match_obj.home_team == match_obj.away_team:
            return JsonResponse({"status": "error", "message": "Tim kandang dan tandang tidak boleh sama."}, status=400)

        # 2. Update Tanggal
        if "date" in data:
            new_date = parse_datetime(data["date"])
            if new_date:
                match_obj.date = new_date

        # 3. Update Skor
        match_obj.home_score = int(data.get("home_score", match_obj.home_score))
        match_obj.away_score = int(data.get("away_score", match_obj.away_score))
        
        # 4. Update Status
        if "is_finished" in data:
             match_obj.status = "FINISHED" if data["is_finished"] else "SCHEDULED"

        match_obj.save()

        return JsonResponse({"status": "success", "message": "Data pertandingan berhasil diperbarui!"}, status=200)

    except Match.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Pertandingan tidak ditemukan."}, status=404)
    except Team.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Tim tidak valid."}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
@csrf_exempt
def delete_match_flutter(request, id):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"status": "error", "message": "Hanya admin yang boleh melakukan ini!"}, status=403)

    try:
        match_obj = Match.objects.get(pk=id)
        match_obj.delete()
        return JsonResponse({"status": "success", "message": "Pertandingan berhasil dihapus!"}, status=200)

    except Match.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Data tidak ditemukan."}, status=404)
    
@csrf_exempt
def edit_team_flutter(request, id):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    
    try:
        team = Team.objects.get(pk=id)
        data = json.loads(request.body)
        
        team.name = data.get("name", team.name)
        team.short_name = data.get("short_name", team.short_name)
        
        team.save()
        
        return JsonResponse({"status": "success", "message": "Data tim berhasil diperbarui!"}, status=200)

    except Team.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Tim tidak ditemukan."}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def delete_team_flutter(request, id):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    
    try:
        team = Team.objects.get(pk=id)
        team.delete()
        return JsonResponse({"status": "success", "message": "Tim berhasil dihapus!"}, status=200)
    except Team.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Tim tidak ditemukan."}, status=404)
    
@csrf_exempt
def league_dashboard_flutter(request):
    """
    API khusus untuk menyediakan data ringkas bagi halaman League Summary di Mobile.
    Logikanya disamakan dengan LeagueDashboardView di Web.
    """
    try:
        # Ambil liga pertama (default logic)
        league = League.objects.first()
        if not league:
            return JsonResponse({"status": "error", "message": "Belum ada data liga."}, status=404)

        # 1. Cari Season Terbaru
        seasons = Match.objects.filter(league=league).values_list("season", flat=True).distinct()
        latest_season = sorted(seasons)[-1] if seasons else None

        # 2. Ambil Klasemen (Hanya 5 teratas untuk preview)
        standings_data = []
        if latest_season:
            top_standings = Standing.objects.filter(
                league=league, season=latest_season
            ).select_related("team").order_by('-points', '-gd', '-gf')[:5]
            
            for s in top_standings:
                standings_data.append({
                    "team_id": s.team.pk,  # <--- WAJIB ADA untuk navigasi ke Detail Tim
                    "team_name": s.team.name,
                    "played": s.played,
                    "points": s.points,
                    "gd": s.gd,
                    "rank": 0 # Nanti diurus di frontend atau enumerate
                })

        # 3. Pertandingan Terakhir Selesai (5 item)
        recent_matches = Match.objects.filter(
            league=league, status=Match.Status.FINISHED
        ).select_related("home_team", "away_team").order_by("-date")[:5]

        recent_data = []
        for m in recent_matches:
            recent_data.append({
                "id": m.pk,
                "home_team": m.home_team.name,
                "away_team": m.away_team.name,
                "home_score": m.home_score,
                "away_score": m.away_score,
                "date": m.date.isoformat(),
                "season": m.season,
            })

        # 4. Pertandingan Akan Datang (5 item)
        now = timezone.now()
        upcoming_matches = Match.objects.filter(
            league=league, date__gt=now
        ).select_related("home_team", "away_team").order_by("date")[:5]

        upcoming_data = []
        for m in upcoming_matches:
            upcoming_data.append({
                "id": m.pk,
                "home_team": m.home_team.name,
                "away_team": m.away_team.name,
                "date": m.date.isoformat(),
                "season": m.season,
            })

        return JsonResponse({
            "status": "success",
            "league_name": league.name,
            "season": latest_season,
            "standings": standings_data,
            "recent_matches": recent_data,
            "upcoming_matches": upcoming_data,
        }, status=200)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
@csrf_exempt
def standings_flutter(request):
    try:
        league = League.objects.first()
        if not league:
            return JsonResponse({"status": "error", "message": "Belum ada data liga."}, status=404)

        # 1. Ambil daftar seasons
        seasons = list(Match.objects.filter(league=league).values_list("season", flat=True).distinct())
        seasons.sort()

        # 2. Tentukan season terpilih
        req_season = request.GET.get("season")
        selected_season = req_season if req_season in seasons else (seasons[-1] if seasons else None)

        # 3. Ambil data Standing
        standings_data = []
        if selected_season:
            qs = Standing.objects.filter(league=league, season=selected_season)\
                .select_related("team").order_by('-points', '-gd', '-gf')

            for rank, s in enumerate(qs, start=1):
                standings_data.append({
                    "id": s.pk,
                    "rank": rank,
                    "team_id": s.team.pk,        # PENTING: ID Tim untuk Admin
                    "league_id": s.league.pk,    # PENTING: ID Liga untuk Admin
                    "team_name": s.team.name,
                    "played": s.played,
                    "win": s.win,
                    "draw": s.draw,
                    "loss": s.loss,
                    "gf": s.gf,
                    "ga": s.ga,
                    "gd": s.gd,
                    "points": s.points,
                })

        return JsonResponse({
            "status": "success",
            "seasons": seasons,
            "selected_season": selected_season,
            "standings": standings_data,
        }, status=200)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
@csrf_exempt
def matches_flutter(request):
    """
    API untuk halaman Jadwal/Matches (Tab 3).
    Mendukung filter ?tab=upcoming|finished|all dan ?q=nama_tim
    """
    try:
        league = League.objects.first()
        if not league:
            return JsonResponse({"status": "error", "message": "Belum ada data liga."}, status=404)

        # 1. Base Queryset
        qs = Match.objects.filter(league=league).select_related("home_team", "away_team").order_by("-date")

        # 2. Filter Tab
        tab = request.GET.get("tab", "all")
        now = timezone.now()
        
        if tab == "upcoming":
            # Urutkan dari yang terdekat (ascending)
            qs = qs.filter(date__gt=now).order_by("date")
        elif tab == "finished":
            # Urutkan dari yang baru selesai (descending)
            qs = qs.filter(status=Match.Status.FINISHED)
        # else "all": default order by -date

        # 3. Filter Search Query (Nama Tim)
        query = request.GET.get("q", "")
        if query:
            qs = qs.filter(Q(home_team__name__icontains=query) | Q(away_team__name__icontains=query))

        # 4. Serialize Data
        matches_data = []
        for m in qs:
            matches_data.append({
                "id": m.pk,
                "home_team": m.home_team.name,
                "home_team_id": m.home_team.pk,
                "away_team": m.away_team.name,
                "away_team_id": m.away_team.pk,
                "home_score": m.home_score,
                "away_score": m.away_score,
                "date": m.date.isoformat(),
                "status": m.status, # SCHEDULED / FINISHED / LIVE / POSTPONED
                "is_finished": m.status == "FINISHED",
                "season": m.season,
            })
        
        return JsonResponse({
            "status": "success",
            "matches": matches_data,
        }, status=200)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
@csrf_exempt
def teams_flutter(request):
    """
    API untuk halaman Daftar Tim (Tab 4).
    Mendukung pencarian ?q=nama_tim
    """
    try:
        league = League.objects.first()
        if not league:
            return JsonResponse({"status": "error", "message": "Belum ada data liga."}, status=404)

        # 1. Base Queryset
        qs = Team.objects.filter(league=league).order_by("name")

        # 2. Filter Search Query
        query = request.GET.get("q", "")
        if query:
            qs = qs.filter(name__icontains=query)

        # 3. Serialize Data
        teams_data = []
        for t in qs:
            teams_data.append({
                "id": t.pk,
                "name": t.name,
                "short_name": t.short_name,
                "founded_year": t.founded_year if t.founded_year else "-",
            })

        return JsonResponse({
            "status": "success",
            "teams": teams_data,
        }, status=200)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
@csrf_exempt
def match_detail_flutter(request, id):
    """
    API untuk detail satu pertandingan (Stats lengkap).
    Digunakan saat kartu pertandingan diklik di mobile.
    """
    try:
        m = Match.objects.get(pk=id)
        data = {
            "id": m.pk,
            "home_team": m.home_team.name,
            "away_team": m.away_team.name,
            "home_score": m.home_score,
            "away_score": m.away_score,
            "date": m.date.isoformat(),
            "status": m.status,
            "season": m.season,
            "is_finished": m.status == "FINISHED",
            
            # --- Statistik Home ---
            "home_shots": m.home_shots,
            "home_shots_on_target": m.home_shots_on_target,
            "home_possession": m.home_possession,
            "home_passes": m.home_passes,
            "home_corners": m.home_corners,
            "home_offsides": m.home_offsides,
            "home_fouls": m.home_fouls_conceded,
            "home_yellow_cards": m.home_yellow_cards,
            "home_red_cards": m.home_red_cards,

            # --- Statistik Away ---
            "away_shots": m.away_shots,
            "away_shots_on_target": m.away_shots_on_target,
            "away_possession": m.away_possession,
            "away_passes": m.away_passes,
            "away_corners": m.away_corners,
            "away_offsides": m.away_offsides,
            "away_fouls": m.away_fouls_conceded,
            "away_yellow_cards": m.away_yellow_cards,
            "away_red_cards": m.away_red_cards,
        }
        return JsonResponse(data, status=200)

    except Match.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Pertandingan tidak ditemukan."}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)