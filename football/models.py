from django.db import models


class League(models.Model):
    """A competition tracked from football-data.org (e.g. Premier League)."""

    code = models.CharField(max_length=10, unique=True)   # e.g. "PL", "PD", "BL1", "SA", "FL1", "WC"
    name = models.CharField(max_length=100)                # e.g. "Premier League"
    emblem_url = models.URLField(blank=True)
    area_name = models.CharField(max_length=100, blank=True)  # e.g. "England"
    is_active = models.BooleanField(default=True)  # turn off a league without deleting its data

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Team(models.Model):
    external_id = models.IntegerField(unique=True)  # football-data.org's team id
    name = models.CharField(max_length=150)
    short_name = models.CharField(max_length=100, blank=True)
    tla = models.CharField(max_length=5, blank=True)  # three-letter code, e.g. "MUN"
    crest_url = models.URLField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Fixture(models.Model):
    STATUS_CHOICES = [
        ("SCHEDULED", "Scheduled"),
        ("LIVE", "Live"),
        ("IN_PLAY", "In Play"),
        ("PAUSED", "Paused"),
        ("FINISHED", "Finished"),
        ("POSTPONED", "Postponed"),
        ("SUSPENDED", "Suspended"),
        ("CANCELLED", "Cancelled"),
    ]

    external_id = models.IntegerField(unique=True)  # football-data.org's match id
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="fixtures")
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_fixtures")
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="away_fixtures")
    utc_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SCHEDULED")
    matchday = models.IntegerField(null=True, blank=True)
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    last_synced = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["utc_date"]
        indexes = [
            models.Index(fields=["league", "status"]),
            models.Index(fields=["utc_date"]),
        ]

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} ({self.utc_date.date()})"


class Standing(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="standings")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="standings")
    position = models.IntegerField()
    played = models.IntegerField(default=0)
    won = models.IntegerField(default=0)
    draw = models.IntegerField(default=0)
    lost = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    goals_for = models.IntegerField(default=0)
    goals_against = models.IntegerField(default=0)
    goal_difference = models.IntegerField(default=0)
    last_synced = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["league", "position"]
        unique_together = [["league", "team"]]

    def __str__(self):
        return f"{self.league.code} #{self.position} {self.team.name}"


class BuzzArticle(models.Model):
    TOPIC_CHOICES = [
        ("transfers", "Transfer News"),
        ("preseason", "Pre-Season Friendlies"),
        ("wc2030", "2030 World Cup Watch"),
        ("aftermath", "Post-WC Fallout"),
    ]

    guid = models.CharField(max_length=500, unique=True)  # RSS entry id/link, used to dedupe
    topic = models.CharField(max_length=20, choices=TOPIC_CHOICES)
    headline = models.CharField(max_length=300)
    body = models.TextField()
    source = models.CharField(max_length=100)   # e.g. "BBC Sport", "Sky Sports"
    url = models.URLField(max_length=500, blank=True)
    published_at = models.DateTimeField()
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [models.Index(fields=["topic", "-published_at"])]

    def __str__(self):
        return f"[{self.topic}] {self.headline[:60]}"
