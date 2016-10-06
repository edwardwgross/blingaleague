import datetime
import decimal

from django import forms
from django.db.models import Q, F
from django.views.generic import TemplateView

from blingaleague.models import FIRST_SEASON, REGULAR_SEASON_WEEKS, \
                                Game, Week, Member, TeamSeason


CHOICE_WINS = 'wins'
CHOICE_LOSSES = 'losses'
CHOICE_WINS_AND_LOSSES = 'wins_and_losses'
CHOICE_REGULAR_SEASON = 'regular'
CHOICE_PLAYOFFS = 'playoffs'
CHOICE_MADE_PLAYOFFS = 'made_playoffs'
CHOICE_MISSED_PLAYOFFS = 'missed_playoffs'


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
    score_min = forms.DecimalField(required=False, label='Minimum Score', decimal_places=2)
    score_max = forms.DecimalField(required=False, label='Maximum Score', decimal_places=2)
    margin_min = forms.DecimalField(required=False, label='Minimum Margin', decimal_places=2)
    margin_max = forms.DecimalField(required=False, label='Maximum Margin', decimal_places=2)
    outcome = forms.TypedChoiceField(required=False, label='Winner / Loser',
        widget=forms.RadioSelect,
        choices=[('', 'Either winner or loser'), (CHOICE_WINS, 'Winner only'), (CHOICE_LOSSES, 'Loser only'), (CHOICE_WINS_AND_LOSSES, 'Both winner and loser')],
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
            wins_and_losses = form_data['outcome'] == CHOICE_WINS_AND_LOSSES

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
            score_winner_kwargs = {}
            score_loser_kwargs = {}
            if score_min is not None and score_max is not None:
                score_winner_kwargs['winner_score__gte'] = score_min
                score_winner_kwargs['winner_score__lte'] = score_max
                score_loser_kwargs['loser_score__gte'] = score_min
                score_loser_kwargs['loser_score__lte'] = score_max
            elif score_min is not None:
                score_winner_kwargs['winner_score__gte'] = score_min
                score_loser_kwargs['loser_score__gte'] = score_min
            elif score_max is not None:
                score_winner_kwargs['winner_score__lte'] = score_max
                score_loser_kwargs['loser_score__lte'] = score_max

            if wins_only:
                games = games.filter(**score_winner_kwargs)
            elif losses_only:
                games = games.filter(**score_loser_kwargs)
            elif wins_and_losses:
                games = games.filter(**score_winner_kwargs)
                games = games.filter(**score_loser_kwargs)
            else:
                games = games.filter(Q(**score_winner_kwargs) | Q(**score_loser_kwargs))

            margin_min= form_data['margin_min']
            margin_max = form_data['margin_max']
            if margin_min is not None:
                games = games.filter(loser_score__lte=F('winner_score') - margin_min)
            if margin_max is not None:
                games = games.filter(loser_score__gte=F('winner_score') - margin_max)

        games = games.order_by('year', 'week', '-winner_score', '-loser_score')

        context = {'form': game_finder_form, 'games': games}

        return self.render_to_response(context)


class SeasonFinderForm(forms.Form):
    year_min = forms.IntegerField(required=False, label='Start Year')
    year_max = forms.IntegerField(required=False, label='End Year')
    week_max = forms.IntegerField(required=False, label='Through Week')
    teams = forms.TypedMultipleChoiceField(required=False, coerce=int, label='Teams',
        widget=forms.CheckboxSelectMultiple,
        choices=[(m.id, m.full_name) for m in Member.objects.all().order_by('first_name', 'last_name')],
    )
    wins_min = forms.IntegerField(required=False, label='Minimum Wins')
    wins_max = forms.IntegerField(required=False, label='Maximum Wins')
    points_min = forms.DecimalField(required=False, label='Minimum Points', decimal_places=2)
    points_max = forms.DecimalField(required=False, label='Maximum Points', decimal_places=2)
    playoffs = forms.TypedChoiceField(required=False, label='Finish',
        widget=forms.RadioSelect,
        choices=[('', 'Any finish'), (CHOICE_MADE_PLAYOFFS, 'Made playoffs'), (CHOICE_MISSED_PLAYOFFS, 'Missed playoffs')],
    )


class SeasonFinderView(TemplateView):
    template_name = 'blingalytics/season_finder.html'

    def filter_seasons(self, form_data):
        year_min = FIRST_SEASON
        year_max = datetime.datetime.today().year
        if form_data['year_min'] is not None:
            year_min = form_data['year_min']
        if form_data['year_max'] is not None:
            year_max = form_data['year_max']

        team_ids = form_data['teams']
        if len(team_ids) == 0:
            team_ids = Member.objects.all().order_by('first_name', 'last_name').values_list('id', flat=True)

        for year in range(year_min, year_max + 1):
            for team_id in team_ids:
                team_season = TeamSeason(team_id, year, week_max=form_data['week_max'])
                if len(team_season.games) == 0:
                    continue

                if form_data['week_max'] is not None:
                    # if the user specified the "Through X Weeks" field,
                    # don't show seasons that haven't yet reached that week
                    if len(team_season.games) < form_data['week_max']:
                        continue

                if form_data['wins_min'] is not None:
                    if team_season.win_count < form_data['wins_min']:
                        continue
                if form_data['wins_max'] is not None:
                    if team_season.win_count > form_data['wins_max']:
                        continue

                if form_data['points_min'] is not None:
                    if team_season.points < form_data['points_min']:
                        continue
                if form_data['points_max'] is not None:
                    if team_season.points > form_data['points_max']:
                        continue

                if form_data['playoffs'] == CHOICE_MADE_PLAYOFFS:
                    if team_season.place_numeric > 6 or len(team_season.games) < REGULAR_SEASON_WEEKS:
                        continue
                elif form_data['playoffs'] == CHOICE_MISSED_PLAYOFFS:
                    if team_season.place_numeric <= 6 or len(team_season.games) < REGULAR_SEASON_WEEKS:
                        continue

                yield team_season

    def get(self, request):
        seasons = []

        season_finder_form = SeasonFinderForm(request.GET)
        if season_finder_form.is_valid():
            form_data = season_finder_form.cleaned_data

            seasons = list(self.filter_seasons(form_data))

        context = {'form': season_finder_form, 'seasons': seasons}

        return self.render_to_response(context)

