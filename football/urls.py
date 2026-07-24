from django.urls import path
from . import views

urlpatterns = [
    path("leagues/", views.api_leagues, name="api-leagues"),
    path("live-scores/", views.api_live_scores, name="api-live-scores"),
    path("standings/", views.api_standings, name="api-standings"),
    path("fixtures/", views.fixtures_board, name="fixtures-board"),
    path("buzz/", views.api_buzz_feed, name="api-buzz"),
]