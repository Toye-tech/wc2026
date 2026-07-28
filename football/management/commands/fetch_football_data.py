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
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone as dt_timezone
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from football.models import League, Team, Fixture, Standing

API_BASE = "https://api.football-data.org/v4"

# Hard ceiling (seconds) on any single call to football-data.org. Enforced
# via a worker thread rather than urlopen's own timeout= parameter, because
# that parameter does NOT cover DNS resolution — DNS lookups can hang
# indefinitely on networks that silently block/throttle a host, regardless
# of any timeout passed to urlopen(). A thread-based deadline catches that
# case too, since it bounds wall-clock time no matter where the call is
# actually stuck.
REQUEST_TIMEOUT = 20

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
        def _do_request():
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                return json.loads(response.read())

        started = time.time()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_do_request)
                result = future.result(timeout=REQUEST_TIMEOUT)
                elapsed = round(time.time() - started, 1)
                self.stdout.write(f"  -> OK in {elapsed}s: {url}")
                return result
        except FuturesTimeoutError:
            self.stderr.write(self.style.WARNING(
                f"  -> TIMED OUT after {REQUEST_TIMEOUT}s calling {url} "
                f"(possibly a DNS or connection block from this network) — skipping."
            ))
            return None
        except urllib.error.HTTPError as e:
            elapsed = round(time.time() - started, 1)
            body = e.read().decode(errors="ignore")
            self.stderr.write(self.style.WARNING(
                f"  -> HTTP {e.code} after {elapsed}s calling {url}: {body[:300]}"
            ))
            return None
        except Exception as e:
            elapsed = round(time.time() - started, 1)
            self.stderr.write(self.style.WARNING(f"  -> FAILED after {elapsed}s calling {url}: {e}"))
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

        total = len(data["matches"])
        self.stdout.write(f"  -> Got {total} matches from API, writing to DB...")

        for i, m in enumerate(data["matches"], start=1):
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
            if i % 20 == 0 or i == total:
                self.stdout.write(f"  -> Wrote {i}/{total} fixtures for {code}")

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
