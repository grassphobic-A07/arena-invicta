from django.db import models
from django.core.validators import MinValueValidator

class League(models.Model):
    name = models.CharField(max_length=100, unique=True, default="Dataset League")
    country = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name
    
class Team(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='teams')
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=10, blank=True)
    founded_year = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('league', 'name')

    def __str__(self):
        return self.name
    
class Match(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        LIVE = "LIVE", "Live"
        FINISHED = "FINISHED", "Finished"
        POSTPONED = "POSTPONED", "Postponed"

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='matches')

    # penting untuk standing per musim
    season = models.CharField(max_length=20) 

    date = models.DateTimeField()

    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.FINISHED)

    # skor FT 
    home_score = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0)])
    away_score = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0)])

    # Statistik ringkas 
    home_clearances = models.PositiveIntegerField(default=0)
    home_corners = models.PositiveIntegerField(default=0)
    home_fouls_conceded = models.PositiveIntegerField(default=0)
    home_offsides = models.PositiveIntegerField(default=0)
    home_passes = models.PositiveIntegerField(default=0)
    home_possession = models.FloatField(default=0.0)
    home_red_cards = models.PositiveIntegerField(default=0)
    home_shots = models.PositiveIntegerField(default=0)
    home_shots_on_target = models.PositiveIntegerField(default=0)
    home_tackles = models.PositiveIntegerField(default=0)
    home_touches = models.PositiveIntegerField(default=0)
    home_yellow_cards = models.PositiveIntegerField(default=0)

    away_clearances = models.PositiveIntegerField(default=0)
    away_corners = models.PositiveIntegerField(default=0)
    away_fouls_conceded = models.PositiveIntegerField(default=0)
    away_offsides = models.PositiveIntegerField(default=0)
    away_passes = models.PositiveIntegerField(default=0)
    away_possession = models.FloatField(default=0.0)
    away_red_cards = models.PositiveIntegerField(default=0)
    away_shots = models.PositiveIntegerField(default=0)
    away_shots_on_target = models.PositiveIntegerField(default=0)
    away_tackles = models.PositiveIntegerField(default=0)
    away_touches = models.PositiveIntegerField(default=0)
    away_yellow_cards = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(check=~models.Q(home_team=models.F('away_team')), name='not_same_team'),
        ]
        ordering = ['date']

    def __str__(self):
        return f"[{self.season}] {self.home_team} vs {self.away_team} ({self.date:%Y-%m-%d})"
    
class Standing(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='standings')
    season = models.CharField(max_length=20)  # sama formatnya dengan di Match.season
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='season_standings')

    played = models.PositiveIntegerField(default=0)
    win = models.PositiveIntegerField(default=0)
    draw = models.PositiveIntegerField(default=0)
    loss = models.PositiveIntegerField(default=0)
    gf = models.IntegerField(default=0)   # goals for
    ga = models.IntegerField(default=0)   # goals against
    gd = models.IntegerField(default=0)   # goal difference
    points = models.IntegerField(default=0)

    class Meta:
        unique_together = ('league', 'season', 'team')
        ordering = ['-points', '-gd', '-gf', 'team__name']

    def __str__(self):
        return f"[{self.season}] {self.team.name} - {self.points} pts"