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
    path('leagues/api/leagues/', views.show_leagues_json, name='show_leagues_json'),
    path('leagues/api/teams/', views.show_teams_json, name='show_teams_json'),
    path('leagues/api/teams/create/', views.create_team_flutter, name='create_team_flutter'),
    path('leagues/api/teams/edit/<int:id>/', views.edit_team_flutter, name='edit_team_flutter'),
    path('leagues/api/teams/delete/<int:id>/', views.delete_team_flutter, name='delete_team_flutter'),
    path('leagues/api/matches/', views.show_matches_json, name='show_matches_json'),
    path('leagues/api/matches/create/', views.create_match_flutter, name='create_match_flutter'),
    path('leagues/api/matches/edit/<int:id>/', views.edit_match_flutter, name='edit_match_flutter'),
    path('leagues/api/matches/delete/<int:id>/', views.delete_match_flutter, name='delete_match_flutter'),
    path('leagues/api/standings/', views.show_standings_json, name='show_standings_json'),
    path('leagues/api/standings/create/', views.create_standing_flutter, name='create_standing_flutter'),
    path('leagues/api/standings/edit/<int:id>/', views.edit_standing_flutter, name='edit_standing_flutter'),
    path('leagues/api/standings/delete/<int:id>/', views.delete_standing_flutter, name='delete_standing_flutter'),
]
