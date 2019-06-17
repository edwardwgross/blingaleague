import decimal
import math
import random

from django.core.management.base import LabelCommand

from blingaleague.models import Season, PLAYOFF_TEAMS


class Command(LabelCommand):

    label = 'year'

    def handle_label(self, year, **kwargs):
        season = Season(int(year))

        teams = []
        for ts in season.standings_table[PLAYOFF_TEAMS:]:
            team_tuple = (
                ts.team.nickname,
                ts.loss_count, ts.points,
            )
            teams.append(team_tuple)

        teams = teams[::-1]  # order worst to best

        losses_weight = decimal.Decimal(0.9)
        points_weight = decimal.Decimal(0.1)

        team_count = len(teams)

        losses_array = []
        points_array = []

        for team in teams:
            losses_array.append(team[1])
            points_array.append(team[2])

        losses_base = min(losses_array) - 1
        points_base = max(points_array) + 50

        total_losses = sum(losses_array) - (team_count * losses_base)
        total_points = (team_count * points_base) - sum(points_array)

        chances = []
        print('Likelihood of getting first pick:')
        for team in teams:
            name = team[0]
            losses = team[1]
            points = team[2]
            losses_chances = losses_weight * (losses - losses_base) / total_losses
            points_chances = points_weight * (points_base - points) / total_points
            overall_chances = losses_chances + points_chances
            print("{}: {:.2f}%".format(name, (100 * overall_chances)))
            chances.append([name, overall_chances])

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
                    for chance in chances:
                        name = chance[0]
                        level = chance[1]
                        total_level = total_level + level
                        if random_value < total_level:
                            if name in used_teams:
                                # don't move onto next team, instead re-generatezd random number
                                break
                            else:
                                used_teams[name] = 1
                                order.append(name)
                                pick_index = pick_index + 1
                                pick_assigned = True
                                break
            outcomes.append(order)
            i = i + 1

        results_by_team = {}
        for team in teams:
            name = team[0]
            results_by_team[name] = [0] * team_count

        for order in outcomes:
            pick_index = 0
            for entry in order:
                results_by_team[entry][pick_index] = results_by_team[entry][pick_index] + 1
                pick_index = pick_index + 1

        print("Actual results after {} runs:".format(max_runs))
        for team in teams:
            name = team[0]
            print("{} {}".format(name.ljust(16), results_by_team[name]))

        print()
        print("RESULTS FOR RANDOMLY SELECTED RUN (#{})".format(run_to_use))
        print(outcomes[run_to_use-1])
