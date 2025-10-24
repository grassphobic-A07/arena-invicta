from django.urls import path
from . import views

app_name = "leagues"

urlpatterns = [
    path("leagues/", views.league_redirect_view, name="league_list"),
    path("leagues/<int:pk>/", views.LeagueDashboardView.as_view(), name="league_dashboard"),
    path("leagues/<int:pk>/matches/", views.MatchListView.as_view(), name="match_list"),
    path("leagues/<int:pk>/standings/", views.StandingsView.as_view(), name="standings"),
    path("leagues/<int:pk>/teams/", views.TeamListView.as_view(), name="team_list"),
    path("teams/<int:team_id>/", views.TeamDetailView.as_view(), name="team_detail"),
    path("matches/<int:match_id>/", views.MatchDetailView.as_view(), name="match_detail"),
    path("matches/<int:match_id>/edit/", views.MatchUpdateView.as_view(), name="match_update"),
    path("matches/<int:match_id>/delete/", views.MatchDeleteView.as_view(), name="match_delete"),
    path("leagues/<int:pk>/matches/new/", views.MatchCreateView.as_view(), name="match_create"),
]
