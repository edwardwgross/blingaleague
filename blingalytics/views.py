import csv
import datetime

from collections import defaultdict

from django.core.cache import caches
from django.db.models import F, ExpressionWrapper, DecimalField
from django.http import HttpResponse
from django.views.generic import TemplateView

from blingaleague.models import Game, Week, Member, TeamSeason, \
                                Season, Matchup, Trade, Keeper, \
                                OUTCOME_WIN, OUTCOME_LOSS, \
                                position_sort_key
from blingaleague.utils import scatter_graph_html, regular_season_weeks

from .forms import CHOICE_BLANGUMS, CHOICE_SLAPPED_HEARTBEAT, \
                   CHOICE_WINS, CHOICE_LOSSES, \
                   CHOICE_REGULAR_SEASON, CHOICE_PLAYOFFS, \
                   CHOICE_MADE_PLAYOFFS, CHOICE_MISSED_PLAYOFFS, \
                   CHOICE_CLINCHED_BYE, CHOICE_CLINCHED_PLAYOFFS, \
                   CHOICE_ELIMINATED_EARLY, \
                   CHOICE_MATCHING_ASSETS_ONLY, \
                   GameFinderForm, SeasonFinderForm, \
                   TradeFinderForm, KeeperFinderForm, \
                   ExpectedWinsCalculatorForm
from .utils import sorted_seasons_by_attr, \
                   sorted_expected_wins_odds, \
                   build_belt_holder_list


CACHE = caches['blingaleague']

PREFIX_WINNER = 'winner'

PREFIX_LOSER = 'loser'

# number of games to qualify for top seasons
# leaderboard for non-counting stats
TOP_SEASONS_GAME_THRESHOLD = 6

TOP_SEASONS_STATS = [
    {
        'title': 'Best Record',
        'attr': 'win_pct',
        'sort_desc': True,
        'require_full_season': True,
        'display_attr': 'record',
    },
    {
        'title': 'Worst Record',
        'attr': 'win_pct',
        'require_full_season': True,
        'display_attr': 'record',
    },
    {
        'title': 'Most Points',
        'attr': 'points',
        'sort_desc': True,
        'min_games': 1,
    },
    {
        'title': 'Fewest Points',
        'attr': 'points',
        'require_full_season': True,
    },
    {
        'title': 'Best Expected Winning Percentage',
        'attr': 'expected_win_pct',
        'sort_desc': True,
    },
    {
        'title': 'Worst Expected Winning Percentage',
        'attr': 'expected_win_pct',
        'require_full_season': True,
    },
    {
        'title': 'Best All-Play Record',
        'attr': 'all_play_win_pct',
        'sort_desc': True,
        'display_attr': 'all_play_record_str',
    },
    {
        'title': 'Worst All-Play Record',
        'attr': 'all_play_win_pct',
        'display_attr': 'all_play_record_str',
    },
    {
        'title': 'Hardest Schedule',
        'attr': 'strength_of_schedule',
        'sort_desc': True,
        'display_attr': 'strength_of_schedule_str',
    },
    {
        'title': 'Easiest Schedule',
        'attr': 'strength_of_schedule',
        'display_attr': 'strength_of_schedule_str',
    },
    {
        'title': 'Most Team Blangums',
        'attr': 'blangums_count',
        'sort_desc': True,
        'min_games': 1,
    },
    {
        'title': 'Most Slapped Heartbeats',
        'attr': 'slapped_heartbeat_count',
        'sort_desc': True,
        'min_games': 1,
    },
    {
        'title': 'Highest Average Score',
        'attr': 'average_score',
        'sort_desc': True,
    },
    {
        'title': 'Lowest Average Score',
        'attr': 'average_score',
    },
    {
        'title': 'Highest Median Score',
        'attr': 'median_score',
        'sort_desc': True,
    },
    {
        'title': 'Lowest Median Score',
        'attr': 'median_score',
    },
    {
        'title': 'Highest Minimum Score',
        'attr': 'min_score',
        'sort_desc': True,
    },
    {
        'title': 'Lowest Maximum Score',
        'attr': 'max_score',
    },
    {
        'title': 'Highest Standard Deviation',
        'attr': 'stdev_score',
        'sort_desc': True,
    },
    {
        'title': 'Lowest Standard Deviation',
        'attr': 'stdev_score',
    },
    {
        'title': 'Standard Deviations Above Average Points',
        'attr': 'zscore_points',
        'sort_desc': True,
    },
    {
        'title': 'Standard Deviations Below Average Points',
        'attr': 'zscore_points',
    },
    {
        'title': 'Standard Deviations Above Average Expected Wins',
        'attr': 'zscore_expected_wins',
        'sort_desc': True,
    },
    {
        'title': 'Standard Deviations Below Average Expected Wins',
        'attr': 'zscore_expected_wins',
    },
    {
        'title': 'Highest Average Margin',
        'attr': 'average_margin',
        'sort_desc': True,
    },
    {
        'title': 'Lowest Average Margin',
        'attr': 'average_margin',
    },
    {
        'title': 'Highest Average Margin in Wins',
        'attr': 'average_margin_win',
        'sort_desc': True,
    },
    {
        'title': 'Lowest Average Margin in Wins',
        'attr': 'average_margin_win',
    },
    {
        'title': 'Highest Average Margin in Losses',
        'attr': 'average_margin_loss',
        'sort_desc': True,
    },
    {
        'title': 'Lowest Average Margin in Losses',
        'attr': 'average_margin_loss',
    },
    {
        'title': 'Longest Winning Streak (single season)',
        'attr': 'longest_winning_streak',
        'sort_desc': True,
        'min_games': 1,
    },
    {
        'title': 'Longest Losing Streak (single season)',
        'attr': 'longest_losing_streak',
        'sort_desc': True,
        'min_games': 1,
    },
]


class CSVResponseMixin(object):

    base_csv_filename = 'blingaleague_{}.csv'

    @property
    def filename(self):
        return self.base_csv_filename.format(
            datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
        )

    def generate_csv_data(self, result_list):
        raise NotImplementedError('Must be defined by the subclass')

    def render_to_csv(self, result_list):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = "attachment; filename={}".format(self.filename)

        csv_writer = csv.writer(response)
        for row in self.generate_csv_data(result_list):
            csv_writer.writerow(row)

        return response


class WeeklyScoresView(TemplateView):
    template_name = 'blingalytics/weekly_scores.html'

    def get(self, request):
        context = {
            'weeks': sorted(
                Week.regular_season_week_list(),
                key=lambda x: (x.year, x.week),
            ),
        }

        return self.render_to_response(context)


class ExpectedWinsView(TemplateView):
    template_name = 'blingalytics/expected_wins.html'

    def _expected_wins_graph(self, score, scaling_function=float):
        min_score = Game.objects.all().order_by('loser_score')[0].loser_score
        max_score = Game.objects.all().order_by('-winner_score')[0].winner_score

        interval = 5
        min_x = interval * (min_score // interval)
        max_x = interval * (max_score // interval) + interval  # add interval to round up

        # add interval because range() is exclusive at the high end
        scores = list(range(int(min_x), int(max_x) + interval, interval))
        if score is not None:
            scores = sorted(scores + [score])

        scores = list(map(float, scores))

        xw_values = []
        for score in scores:
            xw_value = float(scaling_function(Game.expected_wins(score)))
            xw_values.append(min(xw_value, 1))

        custom_options = {
            'title': 'Expected Wins',
            'show_legend': False,
            'x_title': 'Score',
            'value_formatter': lambda x: "{:.3f}".format(x),
            'truncate_label': 3,
            'x_labels_major_count': 6,
            'show_minor_x_labels': False,
            'y_labels': (0, 0.2, 0.4, 0.6, 0.8, 1),
        }

        graph_html = scatter_graph_html(
            scores,  # x_data
            [('', xw_values)],  # y_series
            **custom_options,
        )

        return graph_html

    def get(self, request):
        expected_wins = None
        score = None
        scaling_function = float

        expected_wins_form = ExpectedWinsCalculatorForm(request.GET)
        if expected_wins_form.is_valid():
            form_data = expected_wins_form.cleaned_data
            score = form_data['score']
            year = form_data['year']
            if year:
                scaling_function = Season(year).scale_expected_wins

        if score is not None:
            expected_wins = scaling_function(Game.expected_wins(score))

        context = {
            'form': expected_wins_form,
            'expected_wins': expected_wins,
            'expected_wins_graph_html': self._expected_wins_graph(score, scaling_function),
        }

        return self.render_to_response(context)


class GameFinderView(CSVResponseMixin, TemplateView):
    template_name = 'blingalytics/game_finder.html'

    base_csv_filename = 'game_finder_{}.csv'

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

        margin_min = form_data['margin_min']
        margin_max = form_data['margin_max']
        if margin_min is not None or margin_max is not None:
            base_games = base_games.annotate(
                margin=ExpressionWrapper(
                    F('winner_score') - F('loser_score'),
                    output_field=DecimalField(max_digits=6, decimal_places=2),
                ),
            )
            if margin_min is not None:
                base_games = base_games.filter(margin__gte=margin_min)
            if margin_max is not None:
                base_games = base_games.filter(margin__lte=margin_max)

        wins_only = form_data['outcome'] == CHOICE_WINS
        losses_only = form_data['outcome'] == CHOICE_LOSSES

        teams = form_data['teams']
        score_min = form_data['score_min']
        score_max = form_data['score_max']
        week_type = form_data['week_type']
        awards = form_data['awards']
        streak_min = form_data['streak_min']
        playoff_game_types = form_data['playoff_game_types']

        team_prefixes = (PREFIX_WINNER, PREFIX_LOSER)
        if wins_only:
            team_prefixes = (PREFIX_WINNER,)
        elif losses_only:
            team_prefixes = (PREFIX_LOSER,)

        all_games = []
        for team_prefix in team_prefixes:
            type_kwargs = {}

            if len(teams) > 0:
                type_kwargs["{}__id__in".format(team_prefix)] = teams

            if score_min is not None:
                type_kwargs["{}_score__gte".format(team_prefix)] = score_min
            if score_max is not None:
                type_kwargs["{}_score__lte".format(team_prefix)] = score_max

            opponent_prefix = PREFIX_LOSER if team_prefix == PREFIX_WINNER else PREFIX_WINNER

            for game in base_games.filter(**type_kwargs):
                if week_type == CHOICE_REGULAR_SEASON and game.is_playoffs:
                    continue
                if week_type == CHOICE_PLAYOFFS and not game.is_playoffs:
                    continue

                if CHOICE_BLANGUMS in awards and not game.blangums:
                    continue

                if CHOICE_SLAPPED_HEARTBEAT in awards and not game.slapped_heartbeat:
                    continue

                if playoff_game_types and game.playoff_title_base not in playoff_game_types:
                    continue

                if streak_min is not None:
                    if team_prefix == PREFIX_WINNER and game.winner_streak < streak_min:
                        continue
                    if team_prefix == PREFIX_LOSER and game.loser_streak < streak_min:
                        continue

                outcome = OUTCOME_WIN
                streak = game.winner_streak
                if team_prefix == PREFIX_LOSER:
                    outcome = OUTCOME_LOSS
                    streak = game.loser_streak

                game_dict = {
                    'id': game.id,
                    'year': game.year,
                    'week': game.week,
                    'team': getattr(game, team_prefix),
                    'score': getattr(game, "{}_score".format(team_prefix)),
                    'opponent': getattr(game, opponent_prefix),
                    'opponent_score': getattr(game, "{}_score".format(opponent_prefix)),
                    'margin': game.margin,
                    'outcome': outcome,
                    'streak': streak,
                }

                extra_description = ''
                if game.playoff_title_base:
                    extra_description = game.playoff_title_base
                elif team_prefix == PREFIX_WINNER and game.blangums:
                    extra_description = 'Team Blangums'
                elif team_prefix == PREFIX_LOSER and game.slapped_heartbeat:
                    extra_description = 'Slapped Heartbeat'

                game_dict['extra_description'] = extra_description

                all_games.append(game_dict)

        return sorted(
            all_games,
            key=lambda x: (x['year'], x['week'], -x['score']),
        )

    def build_summary_tables(self, games):
        games_counted = set()
        game_dict = defaultdict(lambda: defaultdict(int))

        for game in games:
            if game['id'] in games_counted:
                continue

            if game['outcome'] == OUTCOME_WIN:
                winner = game['team']
                loser = game['opponent']
                winner_score = game['score']
                loser_score = game['opponent_score']
            else:
                winner = game['opponent']
                loser = game['team']
                winner_score = game['opponent_score']
                loser_score = game['score']

            game_dict[winner]['wins'] += 1
            game_dict[loser]['losses'] += 1
            game_dict[winner]['total'] += 1
            game_dict[loser]['total'] += 1
            game_dict[winner]['points_for'] += winner_score
            game_dict[loser]['points_for'] += loser_score
            game_dict[winner]['points_against'] += loser_score
            game_dict[loser]['points_against'] += winner_score

            games_counted.add(game['id'])

        teams = []
        for team, stats in sorted(game_dict.items(), key=lambda x: x[0].nickname):
            stats['team'] = team
            stats['avg_points_for'] = stats['points_for'] / stats['total']
            stats['avg_points_against'] = stats['points_against'] / stats['total']
            teams.append(stats)

        return {
            'teams': teams,
            'total': len(games_counted),
        }

    def generate_csv_data(self, games):
        csv_data = [
            [
                'Year',
                'Week',
                'Team',
                'W/L',
                'Score',
                'OppScore',
                'Opponent',
                'Margin',
                'Streak',
                'Notes',
            ],
        ]

        for game in games:
            csv_data.append([
                game['year'],
                game['week'],
                game['team'].nickname,
                game['outcome'],
                game['score'],
                game['opponent_score'],
                game['opponent'].nickname,
                game['margin'],
                game['streak'],
                game['extra_description'],
            ])

        return csv_data

    def get(self, request):
        games = []

        game_finder_form = GameFinderForm(request.GET)
        if game_finder_form.is_valid():
            form_data = game_finder_form.cleaned_data

            games = self.filter_games(form_data)

        context = {
            'form': game_finder_form,
            'games': games,
            'summary': self.build_summary_tables(games),
        }

        if 'csv' in request.GET:
            return self.render_to_csv(games)

        return self.render_to_response(context)


class SeasonFinderView(CSVResponseMixin, TemplateView):
    template_name = 'blingalytics/season_finder.html'

    base_csv_filename = 'season_finder_{}.csv'

    def filter_seasons(self, form_data):
        year_min = Season.min().year
        year_max = Season.max().year
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
                ts = TeamSeason(team_id, year, week_max=form_data['week_max'])

                game_count = len(ts.games)
                if game_count == 0:
                    continue

                if form_data['week_max'] is not None:
                    # if the user specified the "Through X Weeks" field,
                    # and the value given is in the regular season,
                    # don't show seasons that haven't yet reached that week
                    # playoffs are special, though - teams with byes won't have the same logic
                    if form_data['week_max'] <= regular_season_weeks(year) or not ts.bye:
                        if game_count < form_data['week_max']:
                            continue
                    elif ts.bye:
                        if game_count < (form_data['week_max'] - 1):
                            continue

                if form_data['wins_min'] is not None:
                    if ts.win_count < form_data['wins_min']:
                        continue
                if form_data['wins_max'] is not None:
                    if ts.win_count > form_data['wins_max']:
                        continue

                if form_data['expected_wins_min'] is not None:
                    if ts.expected_wins < form_data['expected_wins_min']:
                        continue
                if form_data['expected_wins_max'] is not None:
                    if ts.expected_wins > form_data['expected_wins_max']:
                        continue

                if form_data['points_min'] is not None:
                    if ts.points < form_data['points_min']:
                        continue
                if form_data['points_max'] is not None:
                    if ts.points > form_data['points_max']:
                        continue

                if form_data['place_min'] is not None:
                    if ts.place_numeric < form_data['place_min']:
                        continue
                if form_data['place_max'] is not None:
                    if ts.place_numeric > form_data['place_max']:
                        continue

                if form_data['playoffs'] == CHOICE_MADE_PLAYOFFS and not ts.made_playoffs:
                    continue
                elif form_data['playoffs'] == CHOICE_MISSED_PLAYOFFS and not ts.missed_playoffs:
                    continue

                clinched = form_data['clinched']
                if clinched == CHOICE_CLINCHED_BYE and not ts.clinched_bye:
                    continue
                elif clinched == CHOICE_CLINCHED_PLAYOFFS and not ts.clinched_playoffs:
                    continue
                elif clinched == CHOICE_ELIMINATED_EARLY and not ts.eliminated_early:
                    continue

                if form_data['bye'] and not ts.bye:
                    continue

                if form_data['champion'] and not ts.champion:
                    continue

                yield ts

    def build_summary_tables(self, seasons):
        team_dict = defaultdict(int)
        year_dict = defaultdict(int)

        for season in seasons:
            team_dict[season.team] += 1
            year_dict[season.year] += 1

        team_table = sorted(team_dict.items(), key=lambda x: x[0].nickname)
        year_table = sorted(year_dict.items())

        return {
            'teams': team_table,
            'years': year_table,
        }

    def generate_csv_data(self, seasons):
        csv_data = [
            [
                'Year',
                'Team',
                'Wins',
                'Losses',
                'W%',
                'Points',
                'Exp. W',
                'Exp. %',
                'Strength of Schedule',
                'Place',
                'Final Place',
                'Blangums',
                'Slapped Heartbeats',
                'Playoff Finish',
            ],
        ]

        for season in seasons:
            final_place = season.regular_season.place_numeric
            if season.regular_season.is_partial:
                final_place = None

            csv_data.append([
                season.year,
                season.team.nickname,
                season.win_count,
                season.loss_count,
                season.win_pct,
                season.points,
                season.expected_wins,
                season.expected_win_pct,
                season.strength_of_schedule,
                season.place_numeric,
                final_place,
                season.blangums_count,
                season.slapped_heartbeat_count,
                season.playoff_finish,
            ])

        return csv_data

    def get(self, request):
        team_seasons = []

        season_finder_form = SeasonFinderForm(request.GET)
        if season_finder_form.is_valid():
            form_data = season_finder_form.cleaned_data

            team_seasons = list(self.filter_seasons(form_data))

        context = {
            'form': season_finder_form,
            'team_seasons': team_seasons,
            'summary': self.build_summary_tables(team_seasons),
        }

        if 'csv' in request.GET:
            return self.render_to_csv(team_seasons)

        return self.render_to_response(context)


class TradeFinderView(TemplateView):
    template_name = 'blingalytics/trade_finder.html'

    def filter_trades(self, form_data):
        trades = Trade.objects.all()

        if form_data['year_min'] is not None:
            trades = trades.filter(year__gte=form_data['year_min'])
        if form_data['year_max'] is not None:
            trades = trades.filter(year__lte=form_data['year_max'])

        if form_data['week_min'] is not None:
            trades = trades.filter(week__gte=form_data['week_min'])
        if form_data['week_max'] is not None:
            trades = trades.filter(week__lte=form_data['week_max'])

        receivers = form_data['receivers']
        senders = form_data['senders']
        positions = form_data['positions']

        if receivers:
            trades = trades.filter(traded_assets__receiver_id__in=receivers)
        if senders:
            trades = trades.filter(traded_assets__sender_id__in=senders)
        if positions:
            trades = trades.filter(traded_assets__position__in=positions)

        if form_data['includes_draft_picks']:
            trades = trades.filter(traded_assets__is_draft_pick=True)

        return sorted(
            trades.distinct(),
            key=lambda x: (x.year, x.week, x.date),
        )

    def filter_traded_assets(self, trades, form_data):
        assets_to_display = []

        # assume trades is in the desired order
        for trade in trades:
            # sort it as we build, not at the end
            traded_assets = trade.traded_assets.order_by(
                'receiver', 'sender', 'keeper_cost', 'name',
            )

            # user had the option to only show the assets that matched (vs. the full trades)
            if form_data['assets_display'] == CHOICE_MATCHING_ASSETS_ONLY:
                receivers = form_data['receivers']
                senders = form_data['senders']
                positions = form_data['positions']

                if receivers:
                    traded_assets = traded_assets.filter(receiver_id__in=receivers)
                if senders:
                    traded_assets = traded_assets.filter(sender_id__in=senders)
                if positions:
                    traded_assets = traded_assets.filter(position__in=positions)

            assets_to_display.extend(list(traded_assets))

        return assets_to_display

    def build_summary_tables(self, traded_assets):
        all_trade_ids = set()

        team_dict = defaultdict(lambda: {
            'trade_ids': set(),
            'assets_sent': 0,
            'assets_received': 0,
        })

        position_dict = defaultdict(lambda: {
            'trade_ids': set(),
            'assets': 0,
        })

        for asset in traded_assets:
            team_dict[asset.sender]['assets_sent'] += 1
            team_dict[asset.receiver]['assets_received'] += 1
            team_dict[asset.sender]['trade_ids'].add(asset.trade.id)
            team_dict[asset.receiver]['trade_ids'].add(asset.trade.id)

            position_dict[asset.position_display]['assets'] += 1
            position_dict[asset.position_display]['trade_ids'].add(asset.trade.id)

            all_trade_ids.add(asset.trade.id)

        teams = []
        for team, stats in sorted(team_dict.items(), key=lambda x: x[0].nickname):
            stats['team'] = team
            teams.append(stats)

        positions = []
        for position, stats in sorted(position_dict.items(), key=lambda x: position_sort_key(x[0])):
            stats['position'] = position
            positions.append(stats)

        return {
            'teams': teams,
            'positions': positions,
            'total': len(all_trade_ids),
        }

    def get(self, request):
        trades = []
        traded_assets = []

        show_matching_assets_only = False

        trade_finder_form = TradeFinderForm(request.GET)
        if trade_finder_form.is_valid():
            form_data = trade_finder_form.cleaned_data

            # first get a distinct set of matching trades,
            # because the user has the option to show all assets from matching trades
            # later, we build the list of assets to show based on that choice
            trades = list(self.filter_trades(form_data))

            traded_assets = list(self.filter_traded_assets(trades, form_data))

            show_matching_assets_only = form_data['assets_display'] == CHOICE_MATCHING_ASSETS_ONLY

        context = {
            'form': trade_finder_form,
            'trades': sorted(list(trades)),
            'traded_assets': traded_assets,
            'summary': self.build_summary_tables(traded_assets),
            'show_matching_assets_only': show_matching_assets_only,
        }

        return self.render_to_response(context)


class KeeperFinderView(TemplateView):
    template_name = 'blingalytics/keeper_finder.html'

    def filter_keepers(self, form_data):
        keepers = Keeper.objects.all()

        if form_data['year_min'] is not None:
            keepers = keepers.filter(year__gte=form_data['year_min'])
        if form_data['year_max'] is not None:
            keepers = keepers.filter(year__lte=form_data['year_max'])

        if form_data['round_min'] is not None:
            keepers = keepers.filter(round__gte=form_data['round_min'])
        if form_data['round_max'] is not None:
            keepers = keepers.filter(round__lte=form_data['round_max'])

        if form_data['times_kept']:
            keepers = keepers.filter(times_kept__in=form_data['times_kept'])

        if form_data['teams']:
            keepers = keepers.filter(team__id__in=form_data['teams'])

        if form_data['positions']:
            keepers = keepers.filter(position__in=form_data['positions'])

        return sorted(
            keepers,
            key=lambda x: (x.year, x.round, x.team),
        )

    def build_summary_tables(self, keepers):
        team_dict = defaultdict(int)
        round_dict = defaultdict(int)
        position_dict = defaultdict(int)

        for keeper in keepers:
            team_dict[keeper.team] += 1
            round_dict[keeper.round] += 1
            position_dict[keeper.position] += 1

        return {
            'teams': sorted(team_dict.items(), key=lambda x: x[0].nickname),
            'rounds': sorted(round_dict.items()),
            'positions': sorted(position_dict.items(), key=lambda x: position_sort_key(x[0])),
        }

    def get(self, request):
        keepers = []

        keeper_finder_form = KeeperFinderForm(request.GET)
        if keeper_finder_form.is_valid():
            form_data = keeper_finder_form.cleaned_data

            keepers = self.filter_keepers(form_data)

        context = {
            'form': keeper_finder_form,
            'keepers': keepers,
            'summary': self.build_summary_tables(keepers),
        }

        return self.render_to_response(context)


class TopSeasonsView(TemplateView):
    template_name = 'blingalytics/top_seasons.html'

    def generate_top_seasons_tables(self, row_limit, week_max):
        top_seasons_tables = []

        for stat_dict in TOP_SEASONS_STATS:
            title = stat_dict['title']
            attr = stat_dict['attr']
            sort_desc = stat_dict.get('sort_desc', False)
            require_full_season = stat_dict.get('require_full_season', False)
            min_games = stat_dict.get('min_games', TOP_SEASONS_GAME_THRESHOLD)
            display_attr = stat_dict.get('display_attr', None)

            table_rows = sorted_seasons_by_attr(
                attr,
                limit=row_limit,
                sort_desc=sort_desc,
                require_full_season=require_full_season,
                min_games=min_games,
                display_attr=display_attr,
                week_max=week_max,
            )
            top_seasons_tables.append({
                'title': title,
                'rows': table_rows,
            })

        win_odds_categories = (
            # title, win_count
            ('Highest Undefeated Odds', 13),
            ('Highest Winless Odds', 0),
        )

        for title, win_count in win_odds_categories:
            table_rows = sorted_expected_wins_odds(
                win_count,
                limit=row_limit,
                sort_desc=True,
            )
            top_seasons_tables.append({
                'title': title,
                'rows': table_rows,
            })

        return top_seasons_tables

    def get(self, request):
        row_limit = 10
        try:
            row_limit = int(request.GET.get('limit', 10))
        except (ValueError, TypeError):
            # ignore if user passed in a non-int
            pass

        week_max = None
        try:
            week_max = int(request.GET.get('week_max', None))
            if week_max < 1:
                week_max = None
        except (ValueError, TypeError):
            # ignore if user passed in a non-int
            pass

        cache_key = "blingalytics_top_seasons|{}|{}".format(row_limit, week_max)

        if cache_key in CACHE:
            top_seasons_tables = CACHE.get(cache_key)
        else:
            top_seasons_tables = self.generate_top_seasons_tables(row_limit, week_max)
            CACHE.set(cache_key, top_seasons_tables)

        context = {
            'top_seasons_tables': top_seasons_tables,
            'week_max': week_max,
        }

        return self.render_to_response(context)


class TeamVsTeamView(TemplateView):
    template_name = 'blingalytics/team_vs_team.html'

    def get(self, request):
        teams = Member.objects.all().order_by('defunct', 'nickname')

        grid = [{'team': team, 'matchups': Matchup.get_all_for_team(team.id)} for team in teams]

        context = {'grid': grid, 'teams': teams}

        return self.render_to_response(context)


class BeltHolderView(TemplateView):
    template_name = 'blingalytics/belt_holder.html'

    def get(self, request):
        belt_holder_list = build_belt_holder_list()

        belt_stats = defaultdict(lambda: defaultdict(int))
        for holder_data in belt_holder_list:
            holder = holder_data['holder']
            defense_count = holder_data['defense_count']

            belt_stats[holder]['occurrences'] += 1
            belt_stats[holder]['total_defense_count'] += defense_count

        belt_holder_summary = []
        for holder, stats in sorted(belt_stats.items(), key=lambda x: x[0].nickname):
            belt_holder_summary.append({
                'holder': holder,
                'occurrences': stats['occurrences'],
                'total_defense_count': stats['total_defense_count'],
            })

        context = {
            'belt_holder_list': belt_holder_list,
            'belt_holder_summary': belt_holder_summary,
        }

        return self.render_to_response(context)


class GlossaryView(TemplateView):
    template_name = 'blingalytics/glossary.html'
