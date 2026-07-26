"""
Fetches fixtures and standings from football-data.org for a fixed set of
competitions, and upserts them into our own database so the site never
calls the external API directly on a page load.

Run manually:
    python manage.py fetch_football_data

Run on a schedule (every 10-15 minutes is plenty given delayed-score free tier):
    Windows Task Scheduler / cron -> `python manage.py fetch_football_data`
"""

from decouple import config
import time
import socket
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone as dt_timezone

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from football.models import League, Team, Fixture, Standing

# Hard backstop: no single socket operation (including DNS resolution,
# which urllib's per-request timeout parameter doesn't always cover) can
# hang longer than this. Without this, a connection silently blocked or
# throttled by the remote API's network layer can hang indefinitely even
# with a per-call timeout set on urlopen() itself.
socket.setdefaulttimeout(20)

API_BASE = "https://api.football-data.org/v4"

# code -> (Display Name, Area)
COMPETITIONS = {
    "PL":  ("Premier League", "England"),
    "PD":  ("La Liga", "Spain"),
    "BL1": ("Bundesliga", "Germany"),
    "SA":  ("Serie A", "Italy"),
    "FL1": ("Ligue 1", "France"),
}

# Free tier: 10 requests/minute. Sleep between every call to stay well under that.
SLEEP_SECONDS = 7


class Command(BaseCommand):
    help = "Fetch fixtures and standings from football-data.org and cache them locally."

    def handle(self, *args, **options):
        token = config("FOOTBALL_DATA_API_TOKEN", default="")
        if not token:
            self.stderr.write(self.style.ERROR(
                "FOOTBALL_DATA_API_TOKEN is not set in your environment / .env file."
            ))
            return

        headers = {"X-Auth-Token": token}

        for code, (name, area) in COMPETITIONS.items():
            league, _ = League.objects.update_or_create(
                code=code,
                defaults={"name": name, "area_name": area},
            )

            self.stdout.write(f"Fetching matches for {name} ({code})...")
            self._fetch_matches(league, code, headers)
            time.sleep(SLEEP_SECONDS)

            self.stdout.write(f"Fetching standings for {name} ({code})...")
            self._fetch_standings(league, code, headers)
            time.sleep(SLEEP_SECONDS)

        self.stdout.write(self.style.SUCCESS("Football data sync complete."))

    # ------------------------------------------------------------------
    def _get(self, url, headers):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")
            self.stderr.write(self.style.WARNING(
                f"HTTP {e.code} calling {url}: {body[:300]}"
            ))
            return None
        except Exception as e:
            self.stderr.write(self.style.WARNING(f"Error calling {url}: {e}"))
            return None

    # ------------------------------------------------------------------
    def _upsert_team(self, team_data):
        if not team_data or not team_data.get("id"):
            return None
        team, _ = Team.objects.update_or_create(
            external_id=team_data["id"],
            defaults={
                "name": team_data.get("name", "")[:150],
                "short_name": (team_data.get("shortName") or "")[:100],
                "tla": (team_data.get("tla") or "")[:5],
                "crest_url": team_data.get("crest") or "",
            },
        )
        return team

    # ------------------------------------------------------------------
    def _fetch_matches(self, league, code, headers):
        data = self._get(f"{API_BASE}/competitions/{code}/matches", headers)
        if not data or "matches" not in data:
            return

        for m in data["matches"]:
            home_team = self._upsert_team(m.get("homeTeam"))
            away_team = self._upsert_team(m.get("awayTeam"))
            if not home_team or not away_team:
                continue

            score = m.get("score", {}).get("fullTime", {}) or {}
            utc_date = parse_datetime(m["utcDate"])

            Fixture.objects.update_or_create(
                external_id=m["id"],
                defaults={
                    "league": league,
                    "home_team": home_team,
                    "away_team": away_team,
                    "utc_date": utc_date,
                    "status": m.get("status", "SCHEDULED"),
                    "matchday": m.get("matchday"),
                    "home_score": score.get("home"),
                    "away_score": score.get("away"),
                    "venue": m.get("venue") or "",
                },
            )

    # ------------------------------------------------------------------
    def _fetch_standings(self, league, code, headers):
        data = self._get(f"{API_BASE}/competitions/{code}/standings", headers)
        if not data or "standings" not in data:
            return

        # Use the TOTAL table (overall standings), skip HOME/AWAY splits.
        total_table = None
        for block in data["standings"]:
            if block.get("type") == "TOTAL":
                total_table = block.get("table", [])
                break

        if not total_table:
            return

        for row in total_table:
            team = self._upsert_team(row.get("team"))
            if not team:
                continue

            Standing.objects.update_or_create(
                league=league,
                team=team,
                defaults={
                    "position": row.get("position", 0),
                    "played": row.get("playedGames", 0),
                    "won": row.get("won", 0),
                    "draw": row.get("draw", 0),
                    "lost": row.get("lost", 0),
                    "points": row.get("points", 0),
                    "goals_for": row.get("goalsFor", 0),
                    "goals_against": row.get("goalsAgainst", 0),
                    "goal_difference": row.get("goalDifference", 0),
                },
            )
