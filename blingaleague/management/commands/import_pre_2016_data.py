from django.core.management.base import BaseCommand

from blingaleague.models import Game, Season


RAW_NAME_TO_ID = {
    'Ed': 1, 'Matt': 2, 'Rob': 3, 'Kevin': 4, 'Dave': 5,
    'Mike R.': 6, 'Pulley': 7, 'Babel': 8, 'Derrek': 9,
    'Allen': 10, 'Katie': 11, 'Rabbit': 12, 'Pat': 13,
    'Richie': 14, 'Schertz': 15,
}


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        Game.objects.filter(year__lte=2015).delete()

        games_filename = '/data/blingaleague/data/initial_data.csv'

        games_fh = open(games_filename, 'r')

        lines = games_fh.readlines()

        for line in lines:
            year, week, winner, winner_score, loser, loser_score, notes = line.strip().split(',')

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

        Season.objects.all().delete()

        seasons_filename = '/data/blingaleague/data/initial_finishes.csv'

        seasons_fh = open(seasons_filename, 'r')

        lines = seasons_fh.readlines()

        season_kwargs = {}
        for line in lines:
            year, member, place = line.strip().split(',')

            if int(place) <= 6:
                season_kwargs['year'] = year
                season_kwargs["place_%s_id" % place] = RAW_NAME_TO_ID[member]
            elif season_kwargs:
                season = Season(**season_kwargs)
                season.save()
                season_kwargs = {}

        season = Season(year=2016)
        season.save()
