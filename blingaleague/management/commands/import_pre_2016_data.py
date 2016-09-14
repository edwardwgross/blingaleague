from django.core.management.base import BaseCommand

from blingaleague.models import Game


RAW_NAME_TO_ID = {
    'Ed': 1, 'Matt': 2, 'Rob': 3, 'Kevin': 4, 'Dave': 5,
    'Mike R.': 6, 'Pulley': 7, 'Babel': 8, 'Derrek': 9,
    'Allen': 10, 'Katie': 11, 'Rabbit': 12, 'Pat': 13,
    'Richie': 14, 'Schertz': 15,
}
class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        Game.objects.filter(year__lte=2015).delete()

        filename = '/data/blingaleague/data/initial_data.csv'

        fh = open(filename, 'r')

        lines = fh.readlines()

        for line in lines:
            year, week, winner, winner_score, loser, loser_score, notes = line.split(',')

            game_kwargs = {
                'year': year,
                'week': week,
                'winner_id': RAW_NAME_TO_ID[winner],
                'loser_id': RAW_NAME_TO_ID[loser],
                'winner_score': winner_score,
                'loser_score': loser_score,
            }

            if notes:
                game_kwargs['notes'] = notes

            game = Game(**game_kwargs)
            game.save()
