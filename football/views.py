from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from .models import League, Fixture, Standing, BuzzArticle


def fixtures_board(request):
    return render(request, 'football/fixtures.html')


def _team_dict(team):
    return {
        "name": team.name,
        "short_name": team.short_name or team.name,
        "tla": team.tla,
        "crest": team.crest_url,
    }


def _fixture_dict(fixture):
    return {
        "id": fixture.external_id,
        "home_team": _team_dict(fixture.home_team),
        "away_team": _team_dict(fixture.away_team),
        "home_score": fixture.home_score,
        "away_score": fixture.away_score,
        "status": fixture.status,
        "utc_date": fixture.utc_date.isoformat(),
        "matchday": fixture.matchday,
        "venue": fixture.venue,
    }


def api_leagues(request):
    """Returns the list of available leagues for building tab navigation."""
    leagues = League.objects.filter(is_active=True).values("code", "name", "area_name", "emblem_url")
    return JsonResponse({"success": True, "leagues": list(leagues)})


def api_live_scores(request):
    """
    Returns live matches, recent results, and the next upcoming fixtures
    for a given league code. Uses status + limit rather than a fixed date
    window, so it still finds real fixtures even during a season break
    (e.g. the weeks between one season ending and the next kicking off).

    Query params:
        league  - required, e.g. "PL", "PD", "BL1", "SA", "FL1", "WC"
        limit   - optional, how many finished/upcoming fixtures to return (default 5)
    """
    code = request.GET.get("league", "").upper()
    if not code:
        return JsonResponse({"success": False, "error": "league parameter is required"}, status=400)

    league = League.objects.filter(code=code).first()
    if not league:
        return JsonResponse({"success": False, "error": f"Unknown league code '{code}'"}, status=404)

    limit = int(request.GET.get("limit", 5))
    now = timezone.now()

    live_qs = (
        Fixture.objects.filter(league=league, status__in=["LIVE", "IN_PLAY", "PAUSED"])
        .select_related("home_team", "away_team")
        .order_by("utc_date")
    )

    finished_qs = (
        Fixture.objects.filter(league=league, status="FINISHED")
        .select_related("home_team", "away_team")
        .order_by("-utc_date")[:limit]
    )

    upcoming_qs = (
        Fixture.objects.filter(league=league, status="SCHEDULED", utc_date__gte=now)
        .select_related("home_team", "away_team")
        .order_by("utc_date")[:limit]
    )

    # Let the frontend know if the next fixture is more than a few days away
    # (useful for showing "Season resumes in X days" instead of an empty list).
    next_fixture = upcoming_qs[0] if upcoming_qs else None
    days_until_next = None
    if next_fixture:
        days_until_next = (next_fixture.utc_date - now).days

    return JsonResponse({
        "success": True,
        "league": {"code": league.code, "name": league.name},
        "live": [_fixture_dict(f) for f in live_qs],
        "finished": [_fixture_dict(f) for f in finished_qs],
        "upcoming": [_fixture_dict(f) for f in upcoming_qs],
        "days_until_next": days_until_next,
    })


def api_standings(request):
    """
    Returns the league table for a given league code.
    Query params:
        league - required, e.g. "PL", "PD", "BL1", "SA", "FL1"
    """
    code = request.GET.get("league", "").upper()
    if not code:
        return JsonResponse({"success": False, "error": "league parameter is required"}, status=400)

    league = League.objects.filter(code=code).first()
    if not league:
        return JsonResponse({"success": False, "error": f"Unknown league code '{code}'"}, status=404)

    rows = (
        Standing.objects.filter(league=league)
        .select_related("team")
        .order_by("position")
    )

    table = [{
        "position": r.position,
        "team": _team_dict(r.team),
        "played": r.played,
        "won": r.won,
        "draw": r.draw,
        "lost": r.lost,
        "points": r.points,
        "goals_for": r.goals_for,
        "goals_against": r.goals_against,
        "goal_difference": r.goal_difference,
    } for r in rows]

    return JsonResponse({
        "success": True,
        "league": {"code": league.code, "name": league.name},
        "table": table,
    })


# ============================================================
# OFF-SEASON BUZZ — transfer news, pre-season friendlies,
# 2030 World Cup watch, post-WC2026 fallout.
# ============================================================

# Maps our internal topic codes to the "tag" values fixtures.html
# already knows how to style and label.
TOPIC_TO_TAG = {
    "transfers": "transfer",
    "preseason": "friendly",
    "wc2030": "wc2030",
    "aftermath": "controversy",
}


def api_buzz_feed(request):
    """Returns off-season content to keep visitors engaged before
    leagues kick off: transfer news, pre-season friendlies, 2030
    World Cup developments, and post-WC2026 fallout.

    Reads live, auto-fetched articles from BuzzArticle first. Falls
    back to the static BUZZ_SEED content only if nothing's been
    synced yet for that topic."""
    topic = request.GET.get("topic", "transfers")
    limit = int(request.GET.get("limit", 12))

    qs = BuzzArticle.objects.filter(topic=topic).order_by("-published_at")[:limit]

    if qs.exists():
        articles = [{
            "headline": a.headline,
            "body": a.body,
            "tag": TOPIC_TO_TAG.get(a.topic, "general"),
            "time": a.published_at.strftime("%b %d, %Y"),
            "source": a.source,
            "url": a.url,
        } for a in qs]
        return JsonResponse({"success": True, "articles": articles, "live": True})

    return JsonResponse({
        "success": True,
        "articles": BUZZ_SEED.get(topic, BUZZ_SEED["transfers"]),
        "live": False,
    })


# Fallback content only — used when BuzzArticle has no rows yet for a
# given topic (e.g. before fetch_buzz_news has been run for the first
# time, or a topic with no fresh matches on a given sync). Not meant to
# be hand-edited going forward once the automated sync is running.
BUZZ_SEED = {
    "transfers": [
        {"headline": "Newcastle's Anderson Completes British-Record Move to Man City", "body": "Elliot Anderson's transfer from Newcastle to Manchester City is reported to be the most expensive deal ever involving a British player, as City moved fast to beat Manchester United to his signature.", "tag": "transfer", "time": "Jul 21, 2026"},
        {"headline": "Casemiro Reunites with Messi at Inter Miami", "body": "Manchester United's Casemiro has joined Inter Miami, teaming up with Lionel Messi in MLS as the Brazilian midfielder starts a new chapter away from Old Trafford.", "tag": "transfer", "time": "Jul 22, 2026"},
        {"headline": "Ake Ends Man City Spell for Fenerbahce", "body": "Nathan Ake has completed a move to Fenerbahce after six years at Manchester City, one of several senior departures reshaping City's squad this summer.", "tag": "transfer", "time": "Jul 2026"},
        {"headline": "Napoli Appoint Allegri as New Head Coach", "body": "Napoli have confirmed Massimiliano Allegri as their new manager on a contract running to June 2029, a notable managerial change ahead of the new Serie A season.", "tag": "transfer", "time": "Jul 2026"},
        {"headline": "Tchouameni Set to Commit Future to Real Madrid", "body": "Aurelien Tchouameni is expected to sign improved terms at Real Madrid, ending recent speculation about his future at the Bernabeu.", "tag": "transfer", "time": "Jul 2026"},
        {"headline": "Chelsea's Spending Spree Continues", "body": "Chelsea have been among the most active spenders of the summer, with reported outlay running into the billions of euros despite the club's absence from the Champions League this season.", "tag": "transfer", "time": "Jul 22, 2026"},
        {"headline": "Rumour Mill: City Closing on Guimaraes, United Linked with Kone", "body": "Manchester City are reported to be closing in on Newcastle's Bruno Guimaraes, while Manchester United have been linked with Borussia Monchengladbach's Manu Kone as the rumour mill keeps turning through the window.", "tag": "rumour", "time": "Jul 22, 2026"},
        {"headline": "Liverpool Make Cheeky Move for PSG Target", "body": "Liverpool are reported to have made an approach for a winger also being tracked by Paris Saint-Germain, continuing their search for reinforcements out wide.", "tag": "rumour", "time": "Jul 22, 2026"},
    ],
    "preseason": [
        {"headline": "Arsenal's Pre-Season Builds to Community Shield", "body": "Arsenal face Girona, Real Betis in Dublin, Borussia Dortmund and Como at the Emirates before meeting FA Cup winners Manchester City in the Community Shield at Cardiff on August 16.", "tag": "friendly", "time": "Jul\u2013Aug 2026"},
        {"headline": "Man City and Man Utd Head to Asia", "body": "Manchester City travel to Hong Kong and Seoul for friendlies against Inter Milan, K-League All Stars and Atletico Madrid, while Manchester United face Wrexham in Helsinki and Rosenborg in Trondheim on their own pre-season swing.", "tag": "friendly", "time": "Jul\u2013Aug 2026"},
        {"headline": "Chelsea's Australia and Asia Tour", "body": "Chelsea's pre-season takes in Sydney, Hong Kong, Jakarta and Johor, with friendlies against Tottenham, Juventus, AC Milan and Johor Darul Ta'zim before the season begins.", "tag": "friendly", "time": "Jul\u2013Aug 2026"},
        {"headline": "Promoted Trio Prepare for Top-Flight Return", "body": "Coventry City, Hull City and Ipswich Town are all using the pre-season window to prepare for life back in the Premier League, with Coventry hosting Espanyol among their run-in of friendlies.", "tag": "friendly", "time": "Aug 2026"},
        {"headline": "Season Kicks Off August 21", "body": "The 2026/27 Premier League season begins on August 21, with Arsenal returning as reigning champions and welcoming newly promoted Hull City, Coventry City and Ipswich Town to the top flight.", "tag": "general", "time": "Starts Aug 21, 2026"},
        {"headline": "The Fun, Weird Corners of Pre-Season", "body": "As always, pre-season has thrown up some unusual match-ups far from the big-name tours \u2014 South African sides training in Spain, an Austrian friendly between Red Bull Salzburg and CAF champions Mamelodi Sundowns, and Valencia hosting Angolan champions Atletico Petroleos de Luanda.", "tag": "general", "time": "Jul 2026"},
    ],
    "wc2030": [
        {"headline": "2030 World Cup Confirmed for Spain, Portugal and Morocco", "body": "The centenary World Cup will be jointly hosted by Spain, Portugal and Morocco starting June 8, 2030, with symbolic opening matches also staged in Uruguay, Argentina and Paraguay to mark 100 years since the first tournament.", "tag": "wc2030", "time": "Confirmed"},
        {"headline": "Spain Already Qualified as Hosts and Champions", "body": "As both co-hosts and reigning champions, Spain have secured their place at the 2030 tournament, where they'll aim to become the first nation to defend the World Cup since Brazil in 1962.", "tag": "wc2030", "time": "Looking ahead"},
        {"headline": "FIFA Weighing a 64-Team Expansion for 2030 Only", "body": "FIFA president Gianni Infantino has confirmed the governing body will examine a proposal, backed by South American football's governing body, to expand the 2030 edition from 48 to 64 teams as a one-off centenary special. No vote has been scheduled yet.", "tag": "wc2030", "time": "Under discussion"},
        {"headline": "Morocco's Six Host Cities Ramp Up Infrastructure", "body": "Morocco is investing heavily in Rabat, Casablanca, Fes, Tangier, Marrakesh and Agadir ahead of 2030, with stadium renovations, airport expansions and new transport links underway across all six cities.", "tag": "wc2030", "time": "Ongoing"},
        {"headline": "Host City Shortlist Still Being Finalised", "body": "Official venues across the six 2030 host countries are due to be confirmed by the end of 2026, with Madrid, Barcelona and Lisbon each in the running to provide two stadiums apiece.", "tag": "wc2030", "time": "Decision due late 2026"},
    ],
    "aftermath": [
        {"headline": "Halftime Show at the Final Draws Fierce Criticism", "body": "FIFA's decision to stage an extended entertainment show at halftime of the World Cup final was heavily criticised by players and journalists, with one leading football writer calling the disruption to the match's rhythm an \"anti-football\" move.", "tag": "controversy", "time": "Jul 19\u201320, 2026"},
        {"headline": "A Tournament Praised and Picked Apart in Equal Measure", "body": "Post-tournament reviews have highlighted genuine achievements \u2014 a record ten African nations, Canada's first-ever knockout win, a breakout US campaign \u2014 alongside sharp criticism of ticket pricing, refereeing transparency, and allegations of political influence over at least one disciplinary decision.", "tag": "controversy", "time": "Post-tournament"},
        {"headline": "Rosalia Apologises Over Post Seen as Mocking Argentina", "body": "Singer Rosalia apologised after sharing a clip many Argentine fans interpreted as mocking their team's final defeat to Spain, deleting the post following significant backlash on social media.", "tag": "general", "time": "Jul 23, 2026"},
        {"headline": "Spain's Double Cements a Golden Era", "body": "With the men's title added to their existing women's World Cup crown, Spain became the first nation to hold both titles simultaneously \u2014 arguably the standout structural storyline to come out of the tournament's aftermath.", "tag": "general", "time": "Confirmed"},
    ],
}
