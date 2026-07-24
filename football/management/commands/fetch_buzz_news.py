"""
Fetches football news from public RSS feeds, classifies each article into
one of four "buzz" topics by keyword matching, and upserts them into the
database so fixtures.html's Off-Season Buzz section serves fresh content
without any manual editing.

Run manually:
    python manage.py fetch_buzz_news

Run on a schedule (every 30-60 minutes is plenty for news):
    Windows Task Scheduler / cron -> `python manage.py fetch_buzz_news`

Requires the 'feedparser' package:
    pip install feedparser
"""

import calendar
import datetime
from datetime import timezone as dt_timezone, timedelta

import feedparser
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.html import strip_tags

from football.models import BuzzArticle

# (feed url, display name for the "source" field)
FEEDS = [
    ("https://feeds.bbci.co.uk/sport/football/rss.xml", "BBC Sport"),
    ("https://www.skysports.com/rss/12040", "Sky Sports"),
]

# How long to keep articles around before pruning them.
RETENTION_DAYS = 45


def classify_topic(text):
    """
    Simple, transparent keyword classifier. Order matters: check the most
    specific topic (wc2030) first, since a broad "World Cup" match would
    otherwise swallow those articles into 'aftermath'.

    Returns one of the four topic codes, or None if nothing matches
    (in which case the article is skipped — these four buckets are meant
    to stay specific, not catch every football headline that exists).

    Tune these lists freely as you see what the feeds actually produce.
    """
    t = text.lower()

    if any(k in t for k in [
        "2030 world cup", "world cup 2030", "2030 fifa world cup",
        "centenary world cup", "64-team world cup", "64 team world cup",
    ]):
        return "wc2030"

    if any(k in t for k in [
        "pre-season", "preseason", "pre season", "friendly", "friendlies",
        "community shield", "tour opener", "warm-up match",
    ]):
        return "preseason"

    if any(k in t for k in [
        "transfer", "signing", "signs for", "signs a", "loan move",
        "medical ahead", "unveiled as", "completes move", "deal agreed",
        "£", "\u20ac", "done deal", "confirmed signing",
    ]):
        return "transfers"

    if any(k in t for k in [
        "world cup final", "world cup 2026", "wc2026", "golden boot",
        "golden ball", "world cup controversy", "world cup criticism",
        "world cup backlash", "halftime show", "half-time show",
    ]):
        return "aftermath"

    return None


class Command(BaseCommand):
    help = "Fetch football news from RSS feeds, classify by topic, and store in BuzzArticle."

    def handle(self, *args, **options):
        total_new = 0
        total_updated = 0

        for url, source in FEEDS:
            self.stdout.write(f"Fetching {source}...")
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                self.stderr.write(self.style.WARNING(f"Could not parse feed ({source}): {url}"))
                continue

            for entry in feed.entries:
                guid = entry.get("id") or entry.get("link")
                if not guid:
                    continue

                headline = (entry.get("title") or "").strip()
                raw_summary = entry.get("summary") or entry.get("description") or ""
                body = strip_tags(raw_summary).strip()[:500]
                link = entry.get("link", "") or ""

                topic = classify_topic(f"{headline} {body}")
                if not topic:
                    continue  # doesn't match any of our four buckets — skip it

                published_struct = entry.get("published_parsed") or entry.get("updated_parsed")
                if published_struct:
                    published_at = datetime.datetime.fromtimestamp(
                        calendar.timegm(published_struct), tz=dt_timezone.utc
                    )
                else:
                    published_at = timezone.now()

                _, created = BuzzArticle.objects.update_or_create(
                    guid=guid,
                    defaults={
                        "topic": topic,
                        "headline": headline[:300],
                        "body": body,
                        "source": source,
                        "url": link[:500],
                        "published_at": published_at,
                    },
                )
                if created:
                    total_new += 1
                else:
                    total_updated += 1

        # Keep the table from growing forever — old news isn't useful here.
        cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
        deleted, _ = BuzzArticle.objects.filter(published_at__lt=cutoff).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Buzz sync complete — {total_new} new, {total_updated} updated, {deleted} pruned."
        ))