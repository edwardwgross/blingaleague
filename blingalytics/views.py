import decimal

from django import forms
from django.db.models import Q
from django.views.generic import TemplateView

from blingaleague.models import REGULAR_SEASON_WEEKS, Game, Week, Member


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


class GameFinderForm(forms.Form):
    year = forms.IntegerField(required=False)
    week = forms.IntegerField(required=False)
    winner = forms.TypedChoiceField(required=False, coerce=int,
        choices=[('', '')] + [(m.id, m.full_name) for m in Member.objects.all().order_by('first_name', 'last_name')],
    )
    loser = forms.TypedChoiceField(required=False, coerce=int,
        choices=[('', '')] + [(m.id, m.full_name) for m in Member.objects.all().order_by('first_name', 'last_name')],
    )
    winner_score_min = forms.DecimalField(required=False)
    winner_score_max = forms.DecimalField(required=False)
    loser_score_min = forms.DecimalField(required=False)
    loser_score_max = forms.DecimalField(required=False)


class GameFinderView(TemplateView):
    template_name = 'blingalytics/game_finder.html'

    def get(self, request):
        game_finder_form = GameFinderForm(request.GET)

        games = Game.objects.all()

        for arg in ('year', 'week'):
            arg_val = request.GET.get(arg, '')
            if arg_val:
                games = games.filter(**{arg: arg_val})

        winner = request.GET.get('winner', '')
        loser = request.GET.get('loser', '')
        if winner and loser and winner == loser:
            games = games.filter(Q(winner__id=int(winner)) | Q(loser__id=int(loser)))
        else:
            if winner:
                games = games.filter(winner__id=int(winner))
            if loser:
                games = games.filter(loser__id=int(loser))

        winner_score_min = request.GET.get('winner_score_min', '')
        winner_score_max = request.GET.get('winner_score_max', '')
        loser_score_min = request.GET.get('loser_score_min', '')
        loser_score_max = request.GET.get('loser_score_max', '')
        for arg in ('winner_score_min', 'winner_score_max', 'loser_score_min', 'loser_score_max'):
            arg_val = request.GET.get(arg, '')
            if arg_val:
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

        context = {'form': game_finder_form, 'games': games}

        return self.render_to_response(context)
