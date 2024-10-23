from collections import defaultdict, Counter

from django.core.cache import caches
from django.db.models import F, ExpressionWrapper, DecimalField
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, RedirectView

from blingaleague.models import Game, Week, Member, TeamSeason, TeamMultiSeasons, \
                                Season, Matchup, Trade, Keeper, DraftPick, \
                                OUTCOME_WIN, OUTCOME_LOSS, \
                                position_sort_key, calculate_expected_wins
from blingaleague.utils import scatter_graph_html, regular_season_weeks

from .forms import CHOICE_YES, CHOICE_NO, \
                   CHOICE_BLANGUMS, CHOICE_SLAPPED_HEARTBEAT, \
                   CHOICE_WINS, CHOICE_LOSSES, \
                   CHOICE_REGULAR_SEASON, CHOICE_PLAYOFFS, \
                   CHOICE_MADE_PLAYOFFS, CHOICE_MISSED_PLAYOFFS, \
                   CHOICE_CLINCHED_BYE, CHOICE_CLINCHED_PLAYOFFS, \
                   CHOICE_ELIMINATED_EARLY, \
                   CHOICE_MATCHING_ASSETS_ONLY, \
                   GameFinderForm, SeasonFinderForm, \
                   TradeFinderForm, KeeperFinderForm, DraftPickFinderForm, \
                   ExpectedWinsCalculatorForm
from .models import ShortUrl
from .utils import sorted_seasons_by_attr, \
                   build_belt_holder_list, \
                   run_playoff_odds_in_background, \
                   TOP_SEASONS_DEFAULT_NUM_FORMAT


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
        'display_attr': 'record',
    },
    {
        'title': 'Worst Record',
        'attr': 'win_pct',
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
        'title': 'Highest Average Score',
        'attr': 'average_score',
        'sort_desc': True,
    },
    {
        'title': 'Lowest Average Score',
        'attr': 'average_score',
    },
    {
        'title': 'Best Expected Win Pct',
        'attr': 'expected_win_pct',
        'sort_desc': True,
        'num_format': '{:.3f}',
    },
    {
        'title': 'Worst Expected Win Pct',
        'attr': 'expected_win_pct',
        'num_format': '{:.3f}',
    },
    {
        'title': 'Best All-Play Win Pct',
        'attr': 'all_play_win_pct',
        'sort_desc': True,
        'num_format': '{:.3f}',
    },
    {
        'title': 'Worst All-Play Win Pct',
        'attr': 'all_play_win_pct',
        'num_format': '{:.3f}',
    },
    {
        'title': 'Most Points Against',
        'attr': 'points_against',
        'sort_desc': True,
        'min_games': 1,
    },
    {
        'title': 'Fewest Points Against',
        'attr': 'points_against',
        'require_full_season': True,
    },
    {
        'title': 'Highest Average Score Against',
        'attr': 'average_score_against',
        'sort_desc': True,
    },
    {
        'title': 'Lowest Average Score Against',
        'attr': 'average_score_against',
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
    {
        'title': 'Highest Undefeated Odds',
        'attr': 'undefeated_odds',
        'sort_desc': True,
        'require_full_season': True,
        'num_format': '{:.2%}',
    },
    {
        'title': 'Highest Winless Odds',
        'attr': 'winless_odds',
        'sort_desc': True,
        'require_full_season': True,
        'num_format': '{:.2%}',
    },
    {
        'title': 'Highest Odds of First Pick (the following season)',
        'attr': 'first_pick_odds',
        'sort_desc': True,
        'require_full_season': True,
        'num_format': '{:.2%}',
    },
]


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
            xw_values.append(float(scaling_function(calculate_expected_wins(score))))

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
            expected_wins = scaling_function(calculate_expected_wins(score))

        context = {
            'form': expected_wins_form,
            'expected_wins': expected_wins,
            'expected_wins_graph_html': self._expected_wins_graph(score, scaling_function),
        }

        return self.render_to_response(context)


class LongUrlView(TemplateView):

    def render_to_response(self, context):
        url_object, is_new = ShortUrl.objects.get_or_create(full_url=self.request.get_full_path())

        if is_new:
            url_object.save()

        context['short_url'] = url_object.short_url

        return super().render_to_response(context)


class GameFinderView(LongUrlView):
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
        opponents = form_data['opponents']
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

            opponent_prefix = PREFIX_LOSER if team_prefix == PREFIX_WINNER else PREFIX_WINNER
            if len(opponents) > 0:
                type_kwargs["{}__id__in".format(opponent_prefix)] = opponents

            if score_min is not None:
                type_kwargs["{}_score__gte".format(team_prefix)] = score_min
            if score_max is not None:
                type_kwargs["{}_score__lte".format(team_prefix)] = score_max

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
                weekly_rank = game.winner_weekly_rank
                team_season = game.winner_team_season_after_game
                team_season_before_game = game.winner_team_season_before_game
                if team_prefix == PREFIX_LOSER:
                    outcome = OUTCOME_LOSS
                    weekly_rank = game.loser_weekly_rank
                    team_season = game.loser_team_season_after_game
                    team_season_before_game = game.loser_team_season_before_game

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
                    'weekly_rank': weekly_rank,
                    'team_season': team_season,
                    'team_season_before_game': team_season_before_game,
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

    def _build_team_summary_table(self, games, use_opponent=False):
        game_dict = defaultdict(lambda: defaultdict(int))

        for game in games:
            team = game['team']
            points_for = game['score']
            points_against = game['opponent_score']
            is_win = game['outcome'] == OUTCOME_WIN
            if use_opponent:
                team = game['opponent']
                points_for = game['opponent_score']
                points_against = game['score']
                is_win = game['outcome'] == OUTCOME_LOSS

            game_dict[team]['total'] += 1
            game_dict[team]['points_for'] += points_for
            game_dict[team]['points_against'] += points_against
            if is_win:
                game_dict[team]['wins'] += 1
            else:
                game_dict[team]['losses'] += 1

        teams = []
        for team, stats in sorted(game_dict.items()):
            stats['team'] = team
            stats['avg_points_for'] = stats['points_for'] / stats['total']
            stats['avg_points_against'] = stats['points_against'] / stats['total']
            teams.append(stats)

        return teams

    def build_summary_tables(self, games):
        game_ids = set()

        year_dict = defaultdict(int)
        for game in games:
            game_ids.add(game['id'])
            # we don't ignore games_counted for year table, because
            # both the winner and loser should contribute to the counts
            year_dict[game['year']] += 1

        return {
            'teams': self._build_team_summary_table(games),
            'opponents': self._build_team_summary_table(games, use_opponent=True),
            'years': sorted(year_dict.items()),
            'total': len(game_ids),
        }

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

        return self.render_to_response(context)


class SeasonFinderView(LongUrlView):
    template_name = 'blingalytics/season_finder.html'

    def filter_seasons(self, form_data):
        year_min = Season.min().year
        year_max = Season.max().year
        if form_data['year_min'] is not None:
            year_min = form_data['year_min']
        if form_data['year_max'] is not None:
            year_max = form_data['year_max']

        year_span = form_data['year_span']

        team_ids = form_data['teams']
        if len(team_ids) == 0:
            team_ids = Member.objects.all().order_by(
                'nickname', 'first_name', 'last_name',
            ).values_list('id', flat=True)

        for year in range(year_min, year_max + 1):
            for team_id in team_ids:
                if year_span and year_span > 1:
                    # only include multi-season spans that fall completely within
                    # the minimum and maximum year parameters
                    if (year + year_span - 1) > year_max:
                        continue

                    team_season = TeamMultiSeasons(
                        team_id,
                        year_min=year,
                        year_max=year + year_span - 1,
                        week_max=form_data['week_max'],
                    )

                    # only include multi-season spans that have as many seasons with games
                    # as the year span parameter
                    years_with_games = 0
                    for single_season in team_season:
                        if len(single_season.games) > 0:
                            years_with_games += 1

                    if years_with_games < year_span:
                        continue
                else:
                    team_season = TeamSeason(team_id, year, week_max=form_data['week_max'])

                game_count = len(team_season.games)
                if game_count == 0:
                    continue

                if form_data['week_max'] is not None:
                    # if the user specified the "Through X Weeks" field,
                    # and the value given is in the regular season,
                    # don't show seasons that haven't yet reached that week
                    # playoffs are special, though - teams with byes won't have the same logic
                    if form_data['week_max'] <= regular_season_weeks(year) or not team_season.bye:
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

                if form_data['avg_score_min'] is not None:
                    if team_season.average_score < form_data['avg_score_min']:
                        continue
                if form_data['avg_score_max'] is not None:
                    if team_season.average_score > form_data['avg_score_max']:
                        continue

                if year_span is None or year_span == 1:
                    if form_data['place_min'] is not None:
                        if team_season.place_numeric < form_data['place_min']:
                            continue
                    if form_data['place_max'] is not None:
                        if team_season.place_numeric > form_data['place_max']:
                            continue

                if form_data['playoffs'] == CHOICE_MADE_PLAYOFFS and not team_season.made_playoffs:
                    continue
                elif form_data['playoffs'] == CHOICE_MISSED_PLAYOFFS and not team_season.missed_playoffs:  # noqa: E501
                    continue

                clinched = form_data['clinched']
                if clinched == CHOICE_CLINCHED_BYE and not team_season.clinched_bye:
                    continue
                elif clinched == CHOICE_CLINCHED_PLAYOFFS and not team_season.clinched_playoffs:
                    continue
                elif clinched == CHOICE_ELIMINATED_EARLY and not team_season.eliminated_early:
                    continue

                if form_data['bye'] and not team_season.bye:
                    continue

                if form_data['champion'] and not team_season.champion:
                    continue

                yield team_season

    def build_summary_tables(self, team_seasons):
        team_dict = defaultdict(int)
        year_dict = defaultdict(int)

        for team_season in team_seasons:
            team_dict[team_season.team] += 1

            if team_season.is_single_season:
                year_dict[team_season.year] += 1
            else:
                for single_season in team_season:
                    year_dict[single_season.year] += 1

        team_table = sorted(team_dict.items(), key=lambda x: x[0].nickname)
        year_table = sorted(year_dict.items())

        return {
            'teams': team_table,
            'years': year_table,
        }

    def get(self, request):
        team_seasons = []

        is_multi_season_view = False

        season_finder_form = SeasonFinderForm(request.GET)
        if season_finder_form.is_valid():
            form_data = season_finder_form.cleaned_data

            team_seasons = list(self.filter_seasons(form_data))

            if form_data['year_span'] and form_data['year_span'] > 1:
                is_multi_season_view = True

        context = {
            'form': season_finder_form,
            'team_seasons': team_seasons,
            'summary': self.build_summary_tables(team_seasons),
            'is_multi_season_view': is_multi_season_view,
        }

        return self.render_to_response(context)


class TradeFinderView(LongUrlView):
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

        if form_data['player']:
            trades = trades.filter(traded_assets__name__icontains=form_data['player'])

        return sorted(
            trades.distinct(),
            key=lambda x: (x.year, x.week, x.date, x.id),
        )

    def filter_traded_assets(self, trades, form_data):
        assets_to_display = []

        # assume trades is in the desired order
        for trade in trades:
            # sort it as we build, not at the end
            traded_assets = trade.traded_assets.order_by(
                'receiver', 'keeper_cost', 'name', 'sender',
            )

            # user had the option to only show the assets that matched (vs. the full trades)
            if form_data['assets_display'] == CHOICE_MATCHING_ASSETS_ONLY:
                receivers = form_data['receivers']
                senders = form_data['senders']
                positions = form_data['positions']
                player = form_data['player']

                if receivers:
                    traded_assets = traded_assets.filter(receiver_id__in=receivers)
                if senders:
                    traded_assets = traded_assets.filter(sender_id__in=senders)
                if positions:
                    traded_assets = traded_assets.filter(position__in=positions)
                if player:
                    traded_assets = traded_assets.filter(name__icontains=player)

            assets_to_display.extend(list(traded_assets))

        return assets_to_display

    def build_summary_tables(self, traded_assets):
        all_trade_ids = set()

        year_dict = defaultdict(set)

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
            year_dict[asset.trade.year].add(asset.trade.id)

            team_dict[asset.sender]['assets_sent'] += 1
            team_dict[asset.receiver]['assets_received'] += 1
            team_dict[asset.sender]['trade_ids'].add(asset.trade.id)
            team_dict[asset.receiver]['trade_ids'].add(asset.trade.id)

            position_dict[asset.position_display]['assets'] += 1
            position_dict[asset.position_display]['trade_ids'].add(asset.trade.id)

            all_trade_ids.add(asset.trade.id)

        years = []
        for year, trade_ids in sorted(year_dict.items()):
            years.append((year, len(trade_ids)))

        teams = []
        for team, stats in sorted(team_dict.items(), key=lambda x: x[0].nickname):
            stats['team'] = team
            teams.append(stats)

        positions = []
        for position, stats in sorted(position_dict.items(), key=lambda x: position_sort_key(x[0])):
            stats['position'] = position
            positions.append(stats)

        return {
            'years': years,
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


class KeeperFinderView(LongUrlView):
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

        if form_data['player']:
            keepers = keepers.filter(name__icontains=form_data['player'])

        return sorted(
            keepers,
            key=lambda x: (x.year, x.round, x.team),
        )

    def build_summary_tables(self, keepers):
        year_dict = defaultdict(int)
        team_dict = defaultdict(int)
        round_dict = defaultdict(int)
        position_dict = defaultdict(int)

        for keeper in keepers:
            year_dict[keeper.year] += 1
            team_dict[keeper.team] += 1
            round_dict[keeper.round] += 1
            position_dict[keeper.position] += 1

        return {
            'years': sorted(year_dict.items()),
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


class DraftPickFinderView(LongUrlView):
    template_name = 'blingalytics/draft_pick_finder.html'

    def filter_draft_picks(self, form_data):
        base_picks = DraftPick.objects.all()

        if form_data['year_min'] is not None:
            base_picks = base_picks.filter(year__gte=form_data['year_min'])
        if form_data['year_max'] is not None:
            base_picks = base_picks.filter(year__lte=form_data['year_max'])

        if form_data['round_min'] is not None:
            base_picks = base_picks.filter(round__gte=form_data['round_min'])
        if form_data['round_max'] is not None:
            base_picks = base_picks.filter(round__lte=form_data['round_max'])

        if form_data['teams']:
            base_picks = base_picks.filter(team__id__in=form_data['teams'])

        if form_data['positions']:
            base_picks = base_picks.filter(position__in=form_data['positions'])

        if form_data['keeper'] == CHOICE_YES:
            base_picks = base_picks.filter(is_keeper=True)
        elif form_data['keeper'] == CHOICE_NO:
            base_picks = base_picks.filter(is_keeper=False)

        if form_data['traded']:
            base_picks = base_picks.filter(original_team__isnull=False)

        if form_data['player']:
            base_picks = base_picks.filter(name__icontains=form_data['player'])

        draft_picks = []
        for pick in base_picks:
            if form_data['overall_pick_min'] is not None:
                if pick.overall_pick < form_data['overall_pick_min']:
                    continue
            if form_data['overall_pick_max'] is not None:
                if pick.overall_pick > form_data['overall_pick_max']:
                    continue

            draft_picks.append(pick)

        return sorted(
            draft_picks,
            key=lambda x: (x.year, x.overall_pick),
        )

    def build_summary_tables(self, draft_picks):
        year_dict = defaultdict(int)
        team_dict = defaultdict(int)
        round_dict = defaultdict(int)
        position_dict = defaultdict(int)

        for draft_pick in draft_picks:
            year_dict[draft_pick.year] += 1
            team_dict[draft_pick.team] += 1
            round_dict[draft_pick.round] += 1
            position_dict[draft_pick.position] += 1

        return {
            'years': sorted(year_dict.items()),
            'teams': sorted(team_dict.items(), key=lambda x: x[0].nickname),
            'rounds': sorted(round_dict.items()),
            'positions': sorted(position_dict.items(), key=lambda x: position_sort_key(x[0])),
        }

    def get(self, request):
        draft_picks = []

        draft_pick_finder_form = DraftPickFinderForm(request.GET)
        if draft_pick_finder_form.is_valid():
            form_data = draft_pick_finder_form.cleaned_data

            draft_picks = self.filter_draft_picks(form_data)

        context = {
            'form': draft_pick_finder_form,
            'draft_picks': draft_picks,
            'summary': self.build_summary_tables(draft_picks),
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
            num_format = stat_dict.get('num_format', TOP_SEASONS_DEFAULT_NUM_FORMAT)

            table_rows = sorted_seasons_by_attr(
                attr,
                limit=row_limit,
                sort_desc=sort_desc,
                require_full_season=require_full_season,
                min_games=min_games,
                display_attr=display_attr,
                num_format=num_format,
                week_max=week_max,
            )

            # clean up when there is a long list tied for the last spot
            tied_group = {}
            if len(table_rows) > (1.5 * row_limit):
                counts_by_rank = Counter([row['rank'] for row in table_rows])
                max_rank = max(counts_by_rank.keys())
                count_of_max = counts_by_rank[max_rank]

                if count_of_max > (0.5 * row_limit):
                    tied_group['rank'] = max_rank
                    tied_group['count'] = count_of_max
                    tied_group['value'] = table_rows[-1]['value']
                    table_rows = table_rows[0:len(table_rows) - count_of_max]

            if table_rows or tied_group:
                top_seasons_tables.append({
                    'title': title,
                    'rows': table_rows,
                    'tied_group': tied_group,
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


class ShortUrlView(RedirectView):

    def get_redirect_url(self, short_url, **kwargs):
        url_object = get_object_or_404(ShortUrl, short_url=short_url)
        return url_object.full_url


class PlayoffOddsView(TemplateView):
    template_name = 'blingalytics/playoff_odds.html'

    def get(self, request):
        season = Season.latest()

        week_max = None
        if 'year' in request.GET or 'week_max' in request.GET:
            try:
                year = int(request.GET.get('year', season.year))

                week_max = request.GET.get('week_max', None)
                if week_max is not None:
                    week_max = int(week_max)

                season = Season(year, week_max=week_max)
            except (ValueError, TypeError):
                # ignore both if user passed in a non-int
                pass

        playoff_odds_table = []
        results_ready = False
        if season.playoff_odds_cached():
            playoff_odds = season.playoff_odds()

            for team_season in season.standings_table:
                # multiply by 100 to convert to percentages, decimal formatting done in template
                playoffs_raw = 100 * playoff_odds.get(team_season.team, {}).get('playoffs', 0)
                bye_raw = 100 * playoff_odds.get(team_season.team, {}).get('bye', 0)

                # round to the nearest 5% to account for uncertainty and variance of simulations
                playoffs_rounded = 5 * round(playoffs_raw / 5)
                bye_rounded = 5 * round(bye_raw / 5)

                playoff_odds_table.append({
                    'team_season': team_season,
                    'playoff_odds': playoffs_rounded,
                    'bye_odds': bye_rounded,
                })

            results_ready = True
        else:
            run_playoff_odds_in_background(season)

        return self.render_to_response({
            'season': season,
            'playoff_odds_table': playoff_odds_table,
            'week_max': week_max,
            'results_ready': results_ready,
        })
