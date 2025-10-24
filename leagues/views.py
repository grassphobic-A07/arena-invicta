# leagues/views.py

from django.utils import timezone
from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404, redirect, render # <-- Pastikan 'render' ada
from .models import League, Match, Standing, Team
from django.views.generic import TemplateView
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .permissions import is_content_staff
from django.urls import reverse_lazy
from django.views.generic import UpdateView, DeleteView, CreateView
from .forms import MatchUpdateForm, MatchCreateForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect # <-- TAMBAHKAN INI

# TAMBAHKAN HELPER INI (bisa copy dari accounts/views.py)
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