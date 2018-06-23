import datetime
import decimal
import nvd3

from django.db.models import F
from django.views.generic import TemplateView

from blingaleague.models import FIRST_SEASON, REGULAR_SEASON_WEEKS, \
                                Game, Week, Member, TeamSeason

from .forms import CHOICE_BLANGUMS, CHOICE_SLAPPED_HEARTBEAT, \
                   CHOICE_WINS, CHOICE_LOSSES, \
                   CHOICE_REGULAR_SEASON, CHOICE_PLAYOFFS, \
                   CHOICE_MADE_PLAYOFFS, CHOICE_MISSED_PLAYOFFS, \
                   GameFinderForm, SeasonFinderForm


PREFIX_WINNER = 'winner'
PREFIX_LOSER = 'loser'


class WeeklyScoresView(TemplateView):
    template_name = 'blingalytics/weekly_scores.html'

    def get(self, request):
        weeks = []
        games = Game.objects.filter(week__lte=REGULAR_SEASON_WEEKS)
        for year, week in games.values_list('year', 'week').distinct():
            weeks.append(Week(year, week))

        context = {'weeks': sorted(weeks, key=lambda x: (x.year, x.week))}

        return self.render_to_response(context)


class ExpectedWinsView(TemplateView):
    template_name = 'blingalytics/expected_wins.html'

    def _expected_wins_graph(self, score):
        min_score = Game.objects.all().order_by('loser_score')[0].loser_score
        max_score = Game.objects.all().order_by('-winner_score')[0].winner_score

        min_x = int(5 * (min_score // 5))
        max_x = int(5 * (max_score // 5)) + 10
        # add 5 to round up, another 5 because range() is exclusive at the high end

        x_data = list(range(min_x, max_x, 5))
        if score is not None:
            x_data = sorted(x_data + [score])

        x_data = list(map(float, x_data))
        y_data = list(map(float, map(Game.expected_wins, x_data)))

        graph_series = [{'x': x_data, 'y': y_data}]

        graph = nvd3.lineChart(
            name='expected_wins',
            width=600,
            height=400,
            x_axis_format='.2f',
            y_axis_format='.3f',
            show_legend=False,
        )

        for serie in graph_series:
            graph.add_serie(**serie)

        graph.buildcontent()
        graph.buildhtml()

        return graph

    def get(self, request):
        expected_wins = None

        score = request.GET.get('score', None)
        if score is not None:
            score = decimal.Decimal(score)
            expected_wins = Game.expected_wins(score)

        context = {
            'score': score,
            'expected_wins': expected_wins,
            'expected_wins_graph': self._expected_wins_graph(score),
        }

        return self.render_to_response(context)


class GameFinderView(TemplateView):
    template_name = 'blingalytics/game_finder.html'

    def filter_games(self, form_data):
        base_games = Game.objects.all()

        if form_data['year_min'] is not None:
            base_games = base_games.filter(year__gte=form_data['year_min'])
        if form_data['year_max'] is not None:
            base_games = base_games.filter(year__lte=form_data['year_max'])

        if form_data['week_min'] is not None:
            base_games = base_games.filter(week__gte=form_data['week_min'])
        if form_data['week_max'] is not None:
            base_games = base_games.filter(week__lte=form_data['week_max'])

        if form_data['week_type'] == CHOICE_REGULAR_SEASON:
            base_games = base_games.filter(week__lte=REGULAR_SEASON_WEEKS)
        elif form_data['week_type'] == CHOICE_PLAYOFFS:
            base_games = base_games.filter(week__gt=REGULAR_SEASON_WEEKS)

        margin_min = form_data['margin_min']
        margin_max = form_data['margin_max']
        if margin_min is not None:
            base_games = base_games.filter(loser_score__lte=F('winner_score') - margin_min)
        if margin_max is not None:
            base_games = base_games.filter(loser_score__gte=F('winner_score') - margin_max)

        wins_only = form_data['outcome'] == CHOICE_WINS
        losses_only = form_data['outcome'] == CHOICE_LOSSES

        teams = form_data['teams']
        score_min = form_data['score_min']
        score_max = form_data['score_max']
        awards = form_data['awards']

        team_prefixes = (PREFIX_WINNER, PREFIX_LOSER)
        if wins_only:
            team_prefixes = (PREFIX_WINNER,)
        elif losses_only:
            team_prefixes = (PREFIX_LOSER,)

        all_games = []
        for team_prefix in team_prefixes:
            type_kwargs = {}

            if len(teams) > 0:
                type_kwargs["%s__id__in" % team_prefix] = teams

            if score_min is not None:
                type_kwargs["%s_score__gte" % team_prefix] = score_min
            if score_max is not None:
                type_kwargs["%s_score__lte" % team_prefix] = score_max

            opponent_prefix = PREFIX_LOSER if team_prefix == PREFIX_WINNER else PREFIX_WINNER

            for game in base_games.filter(**type_kwargs):
                game_dict = {
                    'year': game.year,
                    'week': game.week,
                    'team': getattr(game, team_prefix),
                    'score': getattr(game, "%s_score" % team_prefix),
                    'opponent': getattr(game, opponent_prefix),
                    'opponent_score': getattr(game, "%s_score" % opponent_prefix),
                    'margin': game.margin,
                    'outcome': 'W' if team_prefix == PREFIX_WINNER else 'L',
                    'blangums': game.blangums,
                    'slapped_heartbeat': game.slapped_heartbeat,
                }

                extra_description = ''
                if game.playoff_title:
                    extra_description = game.playoff_title
                elif team_prefix == PREFIX_WINNER and game.blangums:
                    extra_description = 'Team Blangums'
                elif team_prefix == PREFIX_LOSER and game.slapped_heartbeat:
                    extra_description = 'Slapped Heartbeat'

                game_dict['extra_description'] = extra_description

                all_games.append(game_dict)

        if CHOICE_BLANGUMS in awards:
            all_games = filter(
                lambda x: x['blangums'] and x['week'] <= REGULAR_SEASON_WEEKS,
                all_games,
            )
        if CHOICE_SLAPPED_HEARTBEAT in awards:
            all_games = filter(
                lambda x: x['slapped_heartbeat'] and x['week'] <= REGULAR_SEASON_WEEKS,
                all_games,
            )

        return sorted(all_games, key=lambda x: (x['year'], x['week'], -x['score']))

    def get(self, request):
        games = []

        game_finder_form = GameFinderForm(request.GET)
        if game_finder_form.is_valid():
            form_data = game_finder_form.cleaned_data

            games = self.filter_games(form_data)

        context = {'form': game_finder_form, 'games': games}

        return self.render_to_response(context)


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
            team_ids = Member.objects.all().order_by(
                'nickname', 'first_name', 'last_name',
            ).values_list('id', flat=True)

        for year in range(year_min, year_max + 1):
            for team_id in team_ids:
                team_season = TeamSeason(team_id, year, week_max=form_data['week_max'])

                game_count = len(team_season.games)
                if game_count == 0:
                    continue

                if form_data['week_max'] is not None:
                    # if the user specified the "Through X Weeks" field,
                    # and the value given is in the regular season,
                    # don't show seasons that haven't yet reached that week
                    # playoffs are special, though - teams with byes won't have the same logic
                    if form_data['week_max'] <= REGULAR_SEASON_WEEKS or not team_season.bye:
                        if game_count < form_data['week_max']:
                            continue
                    elif team_season.bye:
                        if game_count < (form_data['week_max'] - 1):
                            continue

                if form_data['wins_min'] is not None:
                    if team_season.win_count < form_data['wins_min']:
                        continue
                if form_data['wins_max'] is not None:
                    if team_season.win_count > form_data['wins_max']:
                        continue

                if form_data['expected_wins_min'] is not None:
                    if team_season.expected_wins < form_data['expected_wins_min']:
                        continue
                if form_data['expected_wins_max'] is not None:
                    if team_season.expected_wins > form_data['expected_wins_max']:
                        continue

                if form_data['points_min'] is not None:
                    if team_season.points < form_data['points_min']:
                        continue
                if form_data['points_max'] is not None:
                    if team_season.points > form_data['points_max']:
                        continue

                if form_data['playoffs'] == CHOICE_MADE_PLAYOFFS and not team_season.playoffs:
                    continue
                elif form_data['playoffs'] == CHOICE_MISSED_PLAYOFFS and team_season.playoffs:
                    continue

                if form_data['bye'] and not team_season.bye:
                    continue

                if form_data['champion'] and not team_season.champion:
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
