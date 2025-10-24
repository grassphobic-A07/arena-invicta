from django.contrib import admin
from .models import League, Team, Match, Standing

@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ("name", "country")
    search_fields = ("name", "country")

    # hilangkan bulk delete jika user tak punya delete
    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm("leagues.delete_league"):
            actions.pop("delete_selected", None)
        return actions

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "league", "short_name", "founded_year")
    list_filter = ("league",)
    search_fields = ("name",)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm("leagues.delete_team"):
            actions.pop("delete_selected", None)
        return actions

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("season","league","date","home_team","away_team","status","home_score","away_score")
    list_filter = ("league","season","status")
    search_fields = ("home_team__name","away_team__name")
    autocomplete_fields = ("league","home_team","away_team")
    date_hierarchy = "date"
    ordering = ("-date",)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm("leagues.delete_match"):
            actions.pop("delete_selected", None)
        return actions

@admin.register(Standing)
class StandingAdmin(admin.ModelAdmin):
    list_display = ("season","league","team","points","played","win","draw","loss","gd","gf","ga")
    list_filter = ("league","season")
    search_fields = ("team__name",)

    # Standing default: view-only untuk Editor (permission diatur via group)
    def has_add_permission(self, request):
        return request.user.has_perm("leagues.add_standing")
    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("leagues.change_standing")
    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("leagues.delete_standing")
    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm("leagues.delete_standing"):
            actions.pop("delete_selected", None)
        return actions
