from collections import defaultdict
from django.db import transaction
from .models import Match, Standing

def recompute_standings_for_league(league):
    """
    Hitung ulang klasemen per season berdasarkan semua Match.status=FINISHED.
    Idempotent: akan 'clear & rebuild' Standing untuk league tsb.
    """
    # Kumpulkan data per (season, team)
    table = defaultdict(lambda: {
        "played": 0, "win": 0, "draw": 0, "loss": 0,
        "gf": 0, "ga": 0, "gd": 0, "points": 0,
    })

    matches = Match.objects.filter(league=league, status=Match.Status.FINISHED) \
                           .select_related("home_team", "away_team")

    for m in matches:
        key_home = (m.season, m.home_team_id)
        key_away = (m.season, m.away_team_id)

        # update dasar
        table[key_home]["played"] += 1
        table[key_away]["played"] += 1

        table[key_home]["gf"] += m.home_score
        table[key_home]["ga"] += m.away_score
        table[key_away]["gf"] += m.away_score
        table[key_away]["ga"] += m.home_score

        # hasil
        if m.home_score > m.away_score:
            table[key_home]["win"] += 1
            table[key_away]["loss"] += 1
            table[key_home]["points"] += 3
        elif m.home_score < m.away_score:
            table[key_away]["win"] += 1
            table[key_home]["loss"] += 1
            table[key_away]["points"] += 3
        else:
            table[key_home]["draw"] += 1
            table[key_away]["draw"] += 1
            table[key_home]["points"] += 1
            table[key_away]["points"] += 1

    # hitung gd
    for k, v in table.items():
        v["gd"] = v["gf"] - v["ga"]

    # simpan ke DB (clear & rebuild)
    with transaction.atomic():
        Standing.objects.filter(league=league).delete()
        bulk = []
        for (season, team_id), agg in table.items():
            bulk.append(Standing(
                league=league,
                season=season,
                team_id=team_id,
                played=agg["played"],
                win=agg["win"],
                draw=agg["draw"],
                loss=agg["loss"],
                gf=agg["gf"],
                ga=agg["ga"],
                gd=agg["gd"],
                points=agg["points"],
            ))
        Standing.objects.bulk_create(bulk, batch_size=1000)
