from django.contrib import admin
from .models import League, Team, Fixture, Standing


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "area_name", "is_active"]
    list_filter = ["is_active"]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "tla", "external_id"]
    search_fields = ["name", "short_name", "tla"]


@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display = ["home_team", "away_team", "league", "utc_date", "status", "home_score", "away_score"]
    list_filter = ["league", "status"]
    ordering = ["-utc_date"]


@admin.register(Standing)
class StandingAdmin(admin.ModelAdmin):
    list_display = ["league", "position", "team", "played", "points"]
    list_filter = ["league"]
    ordering = ["league", "position"]

