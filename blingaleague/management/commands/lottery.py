import math
import random

from django.core.management.base import LabelCommand

from blingaleague.models import Season


class Command(LabelCommand):

    label = 'year'

    def handle_label(self, year, **kwargs):
        season = Season(int(year))

        print('Likelihood of getting first pick:')
        first_pick_odds = [(str(team), odds) for team, odds in season.first_pick_odds]
        for team, odds in first_pick_odds:
            print("{}: {:.2f}%".format(team, (100 * odds)))

        team_count = len(first_pick_odds)

        print()

        i = 0
        max_runs = 10000
        run_to_use = int(math.ceil(max_runs * random.random()))
        outcomes = []
        while i < max_runs:
            pick_index = 0
            used_teams = {}
            order = []
            while pick_index < team_count:
                pick_assigned = False
                while not pick_assigned:
                    random_value = random.random()
                    total_level = 0
                    for team, level in first_pick_odds:
                        total_level = total_level + level
                        if random_value < total_level:
                            if team in used_teams:
                                # don't move onto next team, instead re-generate random number
                                break
                            else:
                                used_teams[team] = 1
                                order.append(team)
                                pick_index = pick_index + 1
                                pick_assigned = True
                                break
            outcomes.append(order)
            i = i + 1

        results_by_team = {}
        for team, _odds in first_pick_odds:
            results_by_team[team] = [0] * team_count

        for order in outcomes:
            pick_index = 0
            for entry in order:
                results_by_team[entry][pick_index] = results_by_team[entry][pick_index] + 1
                pick_index = pick_index + 1

        print("Actual results after {} runs:".format(max_runs))
        for team, _odds in first_pick_odds:
            print("{} {}".format(str(team).ljust(16), results_by_team[team]))

        print()
        print("RESULTS FOR RANDOMLY SELECTED RUN (#{})".format(run_to_use))
        print(
            '\n'.join(
                ["{}. {}".format(pick, team) for pick, team in enumerate(outcomes[run_to_use-1], 1)]
            )
        )
