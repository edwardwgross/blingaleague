import decimal

from django.core.management.base import LabelCommand

from blingaleague.models import Season, regular_season_weeks


class Command(LabelCommand):

    label = 'year'

    def handle_label(self, year, **kwargs):
        season = Season(int(year))

        if season.is_partial:
            return 'Season is not yet finished'

        playoffs_payout_map = {
            1: decimal.Decimal(0.6),
            2: decimal.Decimal(0.3),
            3: decimal.Decimal(0.1),
        }

        dues_amount = 50
        blangums_payout = 20

        total_collected = dues_amount * len(season.standings_table)
        print("Total collected: ${:.0f}".format(total_collected))
        print('')

        playoffs_total = total_collected - regular_season_weeks(year) * blangums_payout

        payouts = []
        total_paid = 0

        for team_season in season.standings_table:
            total_payout = 0

            total_payout += playoffs_total * playoffs_payout_map.get(
                team_season.playoff_finish_numeric,
                0,
            )

            total_payout += blangums_payout * team_season.blangums_count

            payouts.append((total_payout, team_season))
            total_paid += total_payout

        for payout, team_season in sorted(payouts, key=lambda x: (-1 * x[0], x[1])):
            if payout > 0:
                print("- {}: ${:.0f}".format(team_season.team, payout))

        print('')
        print("Total paid out: ${:.0f}".format(total_paid))
