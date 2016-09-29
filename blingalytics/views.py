import decimal

from django import forms
from django.db.models import Q, F
from django.views.generic import TemplateView

from blingaleague.models import REGULAR_SEASON_WEEKS, Game, Week, Member


CHOICE_WINS = 'wins'
CHOICE_LOSSES = 'losses'
CHOICE_REGULAR_SEASON = 'regular'
CHOICE_PLAYOFFS = 'playoffs'


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
    year_min = forms.IntegerField(required=False, label='Start Year')
    year_max = forms.IntegerField(required=False, label='End Year')
    week_type = forms.TypedChoiceField(required=False, label='Weeks',
        widget=forms.RadioSelect,
        choices=[('', 'Any week'), (CHOICE_REGULAR_SEASON, 'Regular season only'), (CHOICE_PLAYOFFS, 'Playoffs only')],
    )
    teams = forms.TypedMultipleChoiceField(required=False, coerce=int, label='Teams',
        widget=forms.CheckboxSelectMultiple,
        choices=[(m.id, m.full_name) for m in Member.objects.all().order_by('first_name', 'last_name')],
    )
    score_min = forms.DecimalField(required=False, label='Minimum Score')
    score_max = forms.DecimalField(required=False, label='Maximum Score')
    margin_min = forms.DecimalField(required=False, label='Minimum Margin')
    margin_max = forms.DecimalField(required=False, label='Maximum Margin')
    outcome = forms.TypedChoiceField(required=False, label='Outcome',
        widget=forms.RadioSelect,
        choices=[('', 'Any outcome'), (CHOICE_WINS, 'Wins only'), (CHOICE_LOSSES, 'Losses only')],
    )


class GameFinderView(TemplateView):
    template_name = 'blingalytics/game_finder.html'

    def get(self, request):
        games = Game.objects.all()

        game_finder_form = GameFinderForm(request.GET)
        if game_finder_form.is_valid():
            form_data = game_finder_form.cleaned_data

            if form_data['year_min'] is not None:
                games = games.filter(year__gte=form_data['year_min'])
            if form_data['year_max'] is not None:
                games = games.filter(year__lte=form_data['year_max'])

            if form_data['week_type'] == CHOICE_REGULAR_SEASON:
                games = games.filter(week__lte=REGULAR_SEASON_WEEKS)
            elif form_data['week_type'] == CHOICE_PLAYOFFS:
                games = games.filter(week__gt=REGULAR_SEASON_WEEKS)

            wins_only = form_data['outcome'] == CHOICE_WINS
            losses_only = form_data['outcome'] == CHOICE_LOSSES

            teams = form_data['teams']
            if len(teams) > 0:
                if wins_only:
                    games = games.filter(winner__id__in=teams)
                elif losses_only:
                    games = games.filter(loser__id__in=teams)
                else:
                    games = games.filter(Q(winner__id__in=teams) | Q(loser__id__in=teams))

            score_min = form_data['score_min']
            score_max = form_data['score_max']
            winner_score_filter = None
            loser_score_filter = None
            has_score_filter = (score_min is not None) or (score_max is not None)
            if score_min is not None and score_max is not None:
                winner_score_filter = Q(winner_score__gte=score_min, winner_score__lte=score_max)
                loser_score_filter = Q(loser_score__gte=score_min, loser_score__lte=score_max)
            elif score_min is not None:
                winner_score_filter = Q(winner_score__gte=score_min)
                loser_score_filter = Q(loser_score__gte=score_min)
            elif score_max is not None:
                winner_score_filter = Q(winner_score__lte=score_max)
                loser_score_filter = Q(loser_score__lte=score_max)

            if has_score_filter:
                score_filter = winner_score_filter | loser_score_filter
                if wins_only:
                    games = games.filter(winner_score_filter)
                elif losses_only:
                    games = games.filter(loser_score_filter)

            margin_min= form_data['margin_min']
            margin_max = form_data['margin_max']
            if margin_min is not None:
                games = games.filter(loser_score__lte=F('winner_score') - margin_min)
            if margin_max is not None:
                games = games.filter(loser_score__gte=F('winner_score') - margin_max)

        games = games.order_by('year', 'week', '-winner_score', '-loser_score')

        context = {'form': game_finder_form, 'games': games}

        return self.render_to_response(context)
