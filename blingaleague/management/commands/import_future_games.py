import sys

from collections import defaultdict

from io import StringIO

from django.core.management.base import LabelCommand

from blingaleague.models import Member, FutureGame


RAW_NAME_TO_ID = {
    'Ed': 1, 'Matt': 2, 'Rob': 3, 'Kevin': 4, 'Dave': 5,
    'Mike R.': 6, 'Pulley': 7, 'Babel': 8, 'Derrek': 9,
    'Allen': 10, 'Katie': 11, 'Rabbit': 12, 'Pat': 13,
    'Richie': 14, 'Schertz': 15, 'Scott': 16,
}

"""
expects a schedule in this format:

Week 1

Team vs. Team
Team vs. Team
...

Week 2

Team vs. Team
Team vs. Team
...

"""


class Command(LabelCommand):

    label = 'year'

    def handle_label(self, year, **kwargs):
        games_by_week = defaultdict(list)

        print("Paste schedule:")
        print('')

        active_week = None
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            if line.startswith('Week'):
                active_week = int(line.split(' ')[1])
            else:
                teams = sorted([part.strip() for part in line.split('vs.')])
                games_by_week[active_week].append([
                    RAW_NAME_TO_ID[teams[0]],
                    RAW_NAME_TO_ID[teams[1]],
                ])

        for week, pairs in sorted(games_by_week.items()):
            for team_1, team_2 in pairs:
                future_game = FutureGame(
                    year=year,
                    week=week,
                    team_1_id=team_1,
                    team_2_id=team_2,
                )
                future_game.save()
