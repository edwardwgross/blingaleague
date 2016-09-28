import decimal

from django.db.models import Q
from django.views.generic import TemplateView

from blingaleague.models import REGULAR_SEASON_WEEKS, Game, Week


class WeeklyScoresView(TemplateView):
    template_name = 'blingalytics/weekly_scores.html'

    def get(self, request):
        weeks = []
        for year, week in Game.objects.filter(week__lte=REGULAR_SEASON_WEEKS).values_list('year', 'week').distinct():
            weeks.append(Week(year, week))

        context = {'weeks': sorted(weeks, key=lambda x: (x.year, x.week))}

        return self.render_to_response(context)


class ExpectedWinsView(TemplateView):
    template_name = 'blingalytics/expected_wins.html'

    def get(self, request):
        expected_wins = None

        score = request.GET.get('score', None)
        if score is not None:
            expected_wins = Game.expected_wins([decimal.Decimal(score)])

        context = {'score': score, 'expected_wins': expected_wins}

        return self.render_to_response(context)


class GameFinderView(TemplateView):
    template_name = 'blingalytics/game_finder.html'

    def get(self, request):
        games = Game.objects.all()

        for arg in ('year', 'week'):
            arg_vals = request.GET.getlist(arg)
            if arg_vals:
                games = games.filter(**{"%s__in" % arg: arg_vals})

        winner = request.GET.get('winner', None)
        loser = request.GET.get('loser', None)
        if winner is not None and loser is not None and winner == loser:
            games = games.filter(Q(winner__id=int(winner)) | Q(loser__id=int(loser)))
        else:
            if winner is not None:
                games = games.filter(winner__id=int(winner))
            if loser is not None:
                games = games.filter(loser__id=int(loser))

        winner_score_min = request.GET.get('winner_score_min', None)
        winner_score_max = request.GET.get('winner_score_max', None)
        loser_score_min = request.GET.get('loser_score_min', None)
        loser_score_max = request.GET.get('loser_score_max', None)
        for arg in ('winner_score_min', 'winner_score_max', 'loser_score_min', 'loser_score_max'):
            arg_val = request.GET.get(arg, None)
            if arg_val is not None:
                arg_val = decimal.Decimal(arg_val)
                field = '_'.join(arg.split('_')[0:2])
                if arg.endswith('_max'):
                    field = "%s__lte" % field
                else:
                    field = "%s__gte" % field
                games = games.filter(**{field: arg_val})

        if 'playoffs' in request.GET:
            games = games.filter(week__gt=REGULAR_SEASON_WEEKS)

        games = games.order_by('year', 'week', '-winner_score', '-loser_score')

        context = {'games': games}

        return self.render_to_response(context)
