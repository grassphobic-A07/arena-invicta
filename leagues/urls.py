from django.urls import path
from . import views

app_name = "leagues"

urlpatterns = [
    # Base league pages (prefixed by /leagues/ from the project urls.py)
    path("", views.league_redirect_view, name="league_list"),
    path("<int:pk>/", views.LeagueDashboardView.as_view(), name="league_dashboard"),
    path("<int:pk>/matches/", views.MatchListView.as_view(), name="match_list"),
    path("<int:pk>/standings/", views.StandingsView.as_view(), name="standings"),
    path("<int:pk>/teams/", views.TeamListView.as_view(), name="team_list"),
    path("teams/<int:team_id>/", views.TeamDetailView.as_view(), name="team_detail"),
    path("matches/<int:match_id>/", views.MatchDetailView.as_view(), name="match_detail"),
    path("matches/<int:match_id>/edit/", views.MatchUpdateView.as_view(), name="match_update"),
    path("matches/<int:match_id>/delete/", views.MatchDeleteView.as_view(), name="match_delete"),
    path("<int:pk>/matches/new/", views.MatchCreateView.as_view(), name="match_create"),
    path('api/leagues/', views.show_leagues_json, name='show_leagues_json'),
    path('api/dashboard/', views.league_dashboard_flutter, name='league_dashboard_flutter'),
    path('api/standings-page/', views.standings_flutter, name='standings_flutter'),
    path('api/matches-page/', views.matches_flutter, name='matches_flutter'),
    path('api/teams-page/', views.teams_flutter, name='teams_flutter'),
    path('api/teams/', views.show_teams_json, name='show_teams_json'),
    path('api/teams/create/', views.create_team_flutter, name='create_team_flutter'),
    path('api/teams/edit/<int:id>/', views.edit_team_flutter, name='edit_team_flutter'),
    path('api/teams/delete/<int:id>/', views.delete_team_flutter, name='delete_team_flutter'),
    path('api/matches/', views.show_matches_json, name='show_matches_json'),
    path('api/matches/<int:id>/', views.match_detail_flutter, name='match_detail_flutter'),
    path('api/matches/create/', views.create_match_flutter, name='create_match_flutter'),
    path('api/matches/edit/<int:id>/', views.edit_match_flutter, name='edit_match_flutter'),
    path('api/matches/delete/<int:id>/', views.delete_match_flutter, name='delete_match_flutter'),
    path('api/standings/', views.show_standings_json, name='show_standings_json'),
    path('api/standings/create/', views.create_standing_flutter, name='create_standing_flutter'),
    path('api/standings/edit/<int:id>/', views.edit_standing_flutter, name='edit_standing_flutter'),
    path('api/standings/delete/<int:id>/', views.delete_standing_flutter, name='delete_standing_flutter'),
]
