import csv
import sys

from io import StringIO

from django.core.management.base import LabelCommand

from blingaleague.models import DraftPick


RAW_NAME_TO_ID = {
    'Ed': 1, 'Matt': 2, 'Rob': 3, 'Kevin': 4, 'Dave': 5,
    'Mike R': 6, 'Pulley': 7, 'Babel': 8, 'Derrek': 9,  # Mike R. has no period on purpose
    'Allen': 10, 'Katie': 11, 'Rabbit': 12, 'Pat': 13,
    'Richie': 14, 'Schertz': 15, 'Scott': 16,
}


class Command(LabelCommand):

    label = 'year'

    def handle_label(self, year, **kwargs):
        raw_board = []

        print("Paste raw CSV of draft board:")
        print('')
        for line in sys.stdin:
            if line.strip():
                for row in csv.reader(StringIO(line)):
                    raw_board.append(list(row))

        team_draft_order = {}
        header_row = raw_board[0]
        for order, raw_team in enumerate(header_row):
            if order == 0:
                # first column is round number, ignore it
                continue

            for team_name, team_id in RAW_NAME_TO_ID.items():
                if team_name in raw_team:
                    team_draft_order[order] = team_id
                    break

        raw_pick_rows = raw_board[1:]
        for round, raw_row in enumerate(raw_pick_rows, 1):
            for order, raw_pick in enumerate(raw_row):
                if order == 0:
                    # first column is round number, ignore it
                    continue

                try:
                    name, position, other_info = raw_pick.split(' - ')
                except Exception:
                    raise ValueError("Error parsing raw pick: {}".format(raw_pick))

                team_id = team_draft_order[order]

                pick_in_round = order
                if round % 2 == 0:
                    pick_in_round = len(team_draft_order) + 1 - order

                is_keeper = False
                if '*' in other_info:
                    is_keeper = True

                notes = None
                if '(' in other_info:
                    notes = other_info[other_info.find('('):][1:-1]

                draft_pick = DraftPick(
                    name=name,
                    position=position,
                    year=year,
                    team_id=team_id,
                    round=round,
                    pick_in_round=pick_in_round,
                    is_keeper=is_keeper,
                    notes=notes,
                )

                draft_pick.save()

                if notes:
                    print("Check PK: {}".format(draft_pick.pk))
