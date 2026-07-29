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
    def _bulk_upsert_teams(self, teams_by_id):
        """Upserts every team in ONE query instead of one round-trip per
        team. Requires Team.external_id to be a real unique/primary-key
        column in the database — if it isn't, add that constraint via a
        migration first, since Postgres needs it to do ON CONFLICT."""
        if not teams_by_id:
            return {}

        team_objs = [
            Team(
                external_id=tid,
                name=t.get("name", "")[:150],
                short_name=(t.get("shortName") or "")[:100],
                tla=(t.get("tla") or "")[:5],
                crest_url=t.get("crest") or "",
            )
            for tid, t in teams_by_id.items()
        ]
        Team.objects.bulk_create(
            team_objs,
            update_conflicts=True,
            unique_fields=["external_id"],
            update_fields=["name", "short_name", "tla", "crest_url"],
        )
        # bulk_create doesn't reliably return PKs for rows that hit the
        # conflict/update path, so one follow-up query builds the id map.
        return {t.external_id: t for t in Team.objects.filter(external_id__in=teams_by_id.keys())}

    # ------------------------------------------------------------------
    def _fetch_matches(self, league, code, headers):
        data = self._get(f"{API_BASE}/competitions/{code}/matches", headers)
        if not data or "matches" not in data:
            return

        matches = data["matches"]
        total = len(matches)
        self.stdout.write(f"  -> Got {total} matches from API")

        # Collect every unique team appearing in this league's fixtures
        # (typically ~20, even though there are hundreds of fixtures) and
        # upsert them all in a single query.
        teams_by_id = {}
        for m in matches:
            for t in (m.get("homeTeam"), m.get("awayTeam")):
                if t and t.get("id"):
                    teams_by_id[t["id"]] = t

        team_map = self._bulk_upsert_teams(teams_by_id)
        self.stdout.write(f"  -> Upserted {len(teams_by_id)} unique teams in 1 query")

        # Build every Fixture row in memory, then write them all in a
        # single bulk upsert instead of one update_or_create per match.
        # This is the change that actually matters: 380 individual writes
        # at ~1-2s of network latency each was the whole bottleneck.
        fixture_objs = []
        for m in matches:
            home = team_map.get((m.get("homeTeam") or {}).get("id"))
            away = team_map.get((m.get("awayTeam") or {}).get("id"))
            if not home or not away:
                continue
            score = m.get("score", {}).get("fullTime", {}) or {}
            fixture_objs.append(Fixture(
                external_id=m["id"],
                league=league,
                home_team=home,
                away_team=away,
                utc_date=parse_datetime(m["utcDate"]),
                status=m.get("status", "SCHEDULED"),
                matchday=m.get("matchday"),
                home_score=score.get("home"),
                away_score=score.get("away"),
                venue=m.get("venue") or "",
            ))

        if fixture_objs:
            Fixture.objects.bulk_create(
                fixture_objs,
                update_conflicts=True,
                unique_fields=["external_id"],
                update_fields=["league", "home_team", "away_team", "utc_date",
                                "status", "matchday", "home_score", "away_score", "venue"],
            )
        self.stdout.write(f"  -> Wrote {len(fixture_objs)}/{total} fixtures for {code} in 1 query")

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

        teams_by_id = {row["team"]["id"]: row["team"] for row in total_table if row.get("team", {}).get("id")}
        team_map = self._bulk_upsert_teams(teams_by_id)

        standing_objs = []
        for row in total_table:
            team = team_map.get((row.get("team") or {}).get("id"))
            if not team:
                continue
            standing_objs.append(Standing(
                league=league,
                team=team,
                position=row.get("position", 0),
                played=row.get("playedGames", 0),
                won=row.get("won", 0),
                draw=row.get("draw", 0),
                lost=row.get("lost", 0),
                points=row.get("points", 0),
                goals_for=row.get("goalsFor", 0),
                goals_against=row.get("goalsAgainst", 0),
                goal_difference=row.get("goalDifference", 0),
            ))

        if standing_objs:
            Standing.objects.bulk_create(
                standing_objs,
                update_conflicts=True,
                unique_fields=["league", "team"],
                update_fields=["position", "played", "won", "draw", "lost",
                                "points", "goals_for", "goals_against", "goal_difference"],
            )
        self.stdout.write(f"  -> Wrote {len(standing_objs)} standings rows for {code} in 1 query")
