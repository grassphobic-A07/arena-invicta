import csv
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from leagues.models import League, Team, Match
from leagues.services import recompute_standings_for_league

CSV_TO_MATCH_FIELDS = {
    "season": "season",
    "date": "date",

    "goal_home_ft": "home_score",
    "goal_away_ft": "away_score",

    "home_clearances": "home_clearances",
    "home_corners": "home_corners",
    "home_fouls_conceded": "home_fouls_conceded",
    "home_offsides": "home_offsides",
    "home_passes": "home_passes",
    "home_possession": "home_possession",
    "home_red_cards": "home_red_cards",
    "home_shots": "home_shots",
    "home_shots_on_target": "home_shots_on_target",
    "home_tackles": "home_tackles",
    "home_touches": "home_touches",
    "home_yellow_cards": "home_yellow_cards",

    "away_clearances": "away_clearances",
    "away_corners": "away_corners",
    "away_fouls_conceded": "away_fouls_conceded",
    "away_offsides": "away_offsides",
    "away_passes": "away_passes",
    "away_possession": "away_possession",
    "away_red_cards": "away_red_cards",
    "away_shots": "away_shots",
    "away_shots_on_target": "away_shots_on_target",
    "away_tackles": "away_tackles",
    "away_touches": "away_touches",
    "away_yellow_cards": "away_yellow_cards",
}

class Command(BaseCommand):
    help = "Import matches from a CSV file and recompute standings per season."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Path to football_matches.csv")
        parser.add_argument("--league-name", default="Dataset League")
        parser.add_argument("--country", default="")

    def handle(self, *args, **opts):
        csv_path = opts["csv"]
        league_name = opts["league_name"]
        country = opts["country"]

        league, _ = League.objects.get_or_create(name=league_name, defaults={"country": country})

        created_matches = 0
        skipped_dup = 0

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                required = {"season","date","home_team","away_team","goal_home_ft","goal_away_ft"}
                missing = required - set(reader.fieldnames or [])
                if missing:
                    raise CommandError(f"CSV missing required columns: {missing}")

                for row in reader:
                    home_name = row["home_team"].strip()
                    away_name = row["away_team"].strip()
                    if not home_name or not away_name:
                        continue

                    home_team, _ = Team.objects.get_or_create(league=league, name=home_name)
                    away_team, _ = Team.objects.get_or_create(league=league, name=away_name)

                    # parse date (naive), Django akan convert ke UTC karena USE_TZ=True
                    date_str = row["date"].strip()
                    dt = datetime.strptime(date_str, "%Y-%m-%d")

                    payload = {
                        "league": league,
                        "season": row["season"].strip(),
                        "date": dt,
                        "home_team": home_team,
                        "away_team": away_team,
                        "status": Match.Status.FINISHED,
                    }

                    for csv_key, model_field in CSV_TO_MATCH_FIELDS.items():
                        if csv_key in ("season","date"):
                            continue

                        val = row.get(csv_key, "").strip()
                        if val == "":
                            if model_field in ("home_possession","away_possession"):
                                payload[model_field] = 0.0
                            else:
                                payload[model_field] = 0
                        else:
                            if model_field in ("home_possession","away_possession"):
                                payload[model_field] = float(val)
                            else:
                                payload[model_field] = int(val)

                    obj, created = Match.objects.get_or_create(
                        league=league,
                        season=payload["season"],
                        date=payload["date"],
                        home_team=payload["home_team"],
                        away_team=payload["away_team"],
                        defaults=payload,
                    )
                    created_matches += int(created)
                    skipped_dup += int(not created)

        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")

        self.stdout.write(self.style.SUCCESS(
            f"Imported: {created_matches}, Skipped duplicates: {skipped_dup}"
        ))

        recompute_standings_for_league(league)
        self.stdout.write(self.style.SUCCESS("Standings recomputed."))
