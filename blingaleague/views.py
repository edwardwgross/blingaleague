import math
import random

from collections import defaultdict

from django.http import Http404
from django.views.generic import TemplateView

from blingacontent.models import Gazette

from .models import Season, Game, Member, \
                    TeamSeason, Week, Matchup, \
                    Trade, Draft, Player, \
                    PLAYOFF_TEAMS, \
                    OUTCOME_WIN, OUTCOME_LOSS, OUTCOME_TIE, OUTCOME_SORT_ORDER
from .utils import line_graph_html, basic_bar_graph_html, stacked_bar_graph_html, \
                   rank_over_time_graph_html, \
                   regular_season_weeks, blingabowl_week


class HomeView(TemplateView):
    template_name = 'blingaleague/home.html'

    def get(self, request):
        latest_season = Season.latest()

        latest_week = Week.latest()
        if latest_week.year != latest_season.year:
            latest_week = None

        all_ts_list = list(TeamSeason.all())
        spotlight_team_seasons = []
        while len(spotlight_team_seasons) < 3:
            random_ts = random.choice(all_ts_list)
            if random_ts not in spotlight_team_seasons and not random_ts.is_current_season:
                spotlight_team_seasons.append(random_ts)

        context = {
            'season': latest_season,
            'week': latest_week,
            'gazette': Gazette.latest(),
            'trades': Trade.most_recent(),
            'spotlight_team_seasons': spotlight_team_seasons,
        }
        return self.render_to_response(context)


class SeasonListView(TemplateView):
    template_name = 'blingaleague/season_list.html'

    def _season_average_graph(self):
        seasons = sorted(Season.all())

        averages_series = defaultdict(list)

        all_time_min = 999
        all_time_max = 0

        years_to_graph = []
        for season in seasons:
            if season.weeks_with_games == 0:
                continue

            mean_score = season.average_game_score
            median_score = season.median_game_score

            averages_series['mean'].append(mean_score)
            averages_series['median'].append(median_score)

            all_time_min = min(all_time_min, mean_score, median_score)
            all_time_max = max(all_time_max, mean_score, median_score)

            years_to_graph.append(season.year)

        interval = 5
        graph_min = int(interval * (all_time_min // interval))
        graph_max = int(interval * (all_time_max // interval) + interval)  # add interval to round up  # noqa: E501
        graph_increments = range(graph_min, graph_max + interval, interval)

        custom_options = {
            'title': 'Average Score',
            'value_formatter': lambda x: '{:.2f}'.format(x),
            'truncate_label': 4,
            'range': (graph_min, graph_max),
            'y_labels': graph_increments,
        }

        graph_html = line_graph_html(
            years_to_graph,  # x_data
            sorted(averages_series.items()),  # y_series
            **custom_options,
        )

        return graph_html

    def get(self, request):
        context = {
            'season_list': sorted(Season.all(), reverse=True),
            'season_averages_graph_html': self._season_average_graph(),
        }
        return self.render_to_response(context)


class SingleSeasonView(TemplateView):
    template_name = 'blingaleague/season.html'

    def _place_by_week_graph(self, season):
        if season.is_upcoming_season:
            return ''

        weeks = sorted(season.standings_table[0].rank_by_week.keys())
        place_series = defaultdict(list)

        for team_season in season.standings_table:
            for week in weeks:
                place_series[team_season.team.nickname].append(
                    team_season.rank_by_week[week]['place'],
                )

        custom_options = {
            'title': 'Weekly Standings',
            'x_title': 'Week',
        }

        graph_html = rank_over_time_graph_html(
            weeks,  # time_data
            place_series,  # raw_rank_series
            len(season.standings_table),  # total_teams
            PLAYOFF_TEAMS,  # rank_cutoff
            **custom_options,
        )

        return graph_html

    def get(self, request, year):
        season_kwargs = {}

        week_max = None
        hide_playoff_finish = False
        if 'week_max' in request.GET:
            try:
                week_max = int(request.GET.get('week_max', regular_season_weeks(year)))
                season_kwargs['week_max'] = week_max
                hide_playoff_finish = week_max < blingabowl_week(year)
            except (ValueError, TypeError):
                # ignore if user passed in a non-int
                pass

        season = Season(year, **season_kwargs)

        weeks_with_games = sorted(set(
            Game.objects.filter(
                year=season.year,
            ).values_list(
                'week',
                flat=True,
            ),
        ))

        context = {
            'season': season,
            'week_max': week_max,
            'weeks_with_games': weeks_with_games,
            'hide_playoff_finish': hide_playoff_finish,
            'place_by_week_graph_html': self._place_by_week_graph(season),
        }

        return self.render_to_response(context)


class GamesView(TemplateView):
    template_name = 'blingaleague/games.html'
    pre_games_sub_templates = tuple()
    post_games_sub_templates = tuple()

    @property
    def games_sub_template(self):
        raise NotImplementedError('Must be defined by the subclass')

    def _context(self, base_object):
        return {
            'base_object': base_object,
            'pre_games_sub_templates': self.pre_games_sub_templates,
            'post_games_sub_templates': self.post_games_sub_templates,
            'games_sub_template': self.games_sub_template,
        }


class MatchupView(GamesView):
    games_sub_template = 'blingaleague/team_vs_team_games.html'

    post_games_sub_templates = (
        'blingaleague/trade_list.html',
    )

    def get(self, request, team1, team2):
        context = self._context(Matchup(team1, team2))
        return self.render_to_response(context)


class WeekView(GamesView):
    post_games_sub_templates = (
        'blingaleague/trade_list.html',
        'blingaleague/standings_sub_page.html',
    )
    games_sub_template = 'blingaleague/weekly_games.html'

    def get(self, request, year, week):
        year = int(year)
        week = int(week)

        context = self._context(Week(year, week))

        context['season'] = Season(year, week_max=week)

        context['hide_playoff_finish'] = week < blingabowl_week(year)

        return self.render_to_response(context)


class TeamListView(TemplateView):
    template_name = 'blingaleague/team_list.html'

    def get(self, request):
        context = {
            'team_list': Member.objects.all(),
            'include_playoffs': 'include_playoffs' in request.GET,
        }
        return self.render_to_response(context)


class TeamSeasonView(GamesView):
    pre_games_sub_templates = (
        'blingaleague/expected_win_distribution_team.html',
    )
    post_games_sub_templates = (
        'blingaleague/team_season_trajectory_graph.html',
        'blingaleague/team_season_trades.html',
        'blingaleague/team_season_draft_picks.html',
        'blingaleague/team_season_keepers.html',
        'blingaleague/team_season_by_week_graphs.html',
        'blingaleague/similar_seasons.html',
    )
    games_sub_template = 'blingaleague/team_season_games.html'

    def _expected_win_distribution_graph(self, team_season):
        expected_win_distribution = sorted(team_season.expected_win_distribution.items())
        wins = list(map(lambda x: x[0], expected_win_distribution))
        odds = list(map(lambda x: float(x[1]), expected_win_distribution))

        custom_options = {
            'title': 'Expected Win Distribution',
            'height': 240,
            'show_legend': False,
            'x_title': 'Wins',
            'value_formatter': lambda x: "{:.1f}%".format(100 * x),
        }

        graph_html = basic_bar_graph_html(
            wins,  # x_data
            [('', odds)],  # y_series
            **custom_options,
        )

        return graph_html

    def _rank_by_week_graph(self, team_season):
        if team_season.season_object.is_upcoming_season:
            return ''

        weeks = sorted(team_season.rank_by_week.keys())
        rank_series = defaultdict(list)

        for week in weeks:
            ranks = team_season.rank_by_week[week]
            for name, value in ranks.items():
                rank_series[name].append(value)

        custom_options = {
            'title': 'Rank by Week',
            'x_title': 'Week',
        }

        graph_html = rank_over_time_graph_html(
            weeks,  # time_data
            rank_series,  # raw_rank_series
            len(Season(team_season.year).standings_table),  # total_teams
            PLAYOFF_TEAMS,  # rank_cutoff
            **custom_options,
        )

        return graph_html


    def _expected_wins_by_week_graph(self, team_season):
        if team_season.season_object.is_upcoming_season:
            return

        weeks = []
        expected_wins_by_outcome = defaultdict(lambda: [None] * len(team_season.games))

        for week, expected_wins in enumerate(team_season.expected_wins_by_game, 1):
            if week > regular_season_weeks(team_season.year):
                break

            weeks.append(week)

            outcome = team_season.week_outcome(week)

            expected_wins_by_outcome[outcome][week - 1] = expected_wins

        custom_options = {
            'title': 'Expected Wins by Week',
            'height': 240,
            'min_scale': 0,
            'max_scale': 1,
            'x_title': 'Week',
            'y_labels': [0, 0.5, 1],
            'value_formatter': lambda x: "{:.3f}".format(x),
        }

        by_outcome_data = [
            ('Won game', expected_wins_by_outcome[OUTCOME_WIN]),
            ('Lost game', expected_wins_by_outcome[OUTCOME_LOSS]),
        ]

        graph_html = stacked_bar_graph_html(
            weeks,  # x_data
            by_outcome_data,  # y_series
            **custom_options,
        )

        return graph_html

    def _all_play_wins_by_week_graph(self, team_season):
        if team_season.season_object.is_upcoming_season:
            return ''

        weeks = []
        all_play_wins = []

        all_play_wins_by_outcome = defaultdict(lambda: [None] * len(team_season.games))

        value_format = '{:.0f}'

        for i, game in enumerate(team_season.games):
            if game.week_object.is_playoffs:
                break

            weeks.append(game.week)

            outcome = team_season.week_outcome(game.week)

            all_play_record = game.week_object.all_play_record(team_season.team)

            if all_play_record[OUTCOME_TIE] > 0:
                value_format = '{:.1f}'

            all_play_wins = all_play_record[OUTCOME_WIN] + all_play_record[OUTCOME_TIE] / 2
            all_play_wins_by_outcome[outcome][i] = all_play_wins

        total_teams = len(team_season.season_object.standings_table)

        custom_options = {
            'title': 'All-Play Wins by Week',
            'height': 240,
            'min_scale': total_teams - 1,
            'max_scale': total_teams - 1,
            'range': (0, total_teams - 1),
            'x_title': 'Week',
            'y_labels': [0, math.ceil(total_teams / 2), total_teams - 1],
            'value_formatter': lambda x: value_format.format(x),
        }

        by_outcome_data = [
            ('Won game', all_play_wins_by_outcome[OUTCOME_WIN]),
            ('Lost game', all_play_wins_by_outcome[OUTCOME_LOSS]),
        ]

        graph_html = stacked_bar_graph_html(
            weeks,  # x_data
            by_outcome_data,  # y_series
            **custom_options,
        )

        return graph_html

    def get(self, request, team, year):
        week_max = request.GET.get('week_max', None)

        if week_max is not None:
            try:
                week_max = int(week_max)
                # regardless of given value, cap at the number of total weeks
                week_max = min(week_max, blingabowl_week(year))
            except (ValueError, TypeError):
                # ignore if user passed in a non-int
                week_max = None

        team_season = TeamSeason(
            team,
            year,
            include_playoffs=True,
            week_max=week_max,
        )

        context = self._context(team_season)

        if team_season.active:
            context['expected_win_distribution_graph_html'] = self._expected_win_distribution_graph(team_season)  # noqa: E501
            context['rank_by_week_graph_html'] = self._rank_by_week_graph(team_season)
            context['expected_wins_by_week_graph'] = self._expected_wins_by_week_graph(team_season)
            context['all_play_wins_by_week_graph'] = self._all_play_wins_by_week_graph(team_season)

        return self.render_to_response(context)


class TeamDetailsView(TemplateView):
    template_name = 'blingaleague/team_details.html'

    def _rank_by_year_graph(self, team):
        years = []
        rank_series = defaultdict(list)

        total_teams = 0

        for team_season in team.seasons:
            if len(team_season.games) == 0:
                continue

            years.append(team_season.year)

            final_week = max(team_season.rank_by_week.keys())
            final_ranks = team_season.rank_by_week[final_week]

            for name, value in final_ranks.items():
                rank_series[name].append(value)

            team_count = len(Season(team_season.year).standings_table)
            if team_count > total_teams:
                total_teams = team_count

        custom_options = {
            'title': 'Rank by Season',
            'truncate_label': 4,
        }

        return rank_over_time_graph_html(
            years,  # time_data
            rank_series,  # raw_rank_series
            total_teams,
            PLAYOFF_TEAMS,  # rank_cutoff
            **custom_options,
        )

    def get(self, request, team):
        team = Member.objects.get(id=team)
        context = {
            'team': team,
            'rank_by_year_graph_html': self._rank_by_year_graph(team),
        }
        return self.render_to_response(context)


class TradeView(TemplateView):
    template_name = 'blingaleague/trade_base.html'

    def get(self, request, trade):
        trade = Trade.objects.get(id=trade)
        context = {'trade': trade}
        return self.render_to_response(context)


class DraftView(TemplateView):
    template_name = 'blingaleague/draft.html'

    def get(self, request, year):
        draft = Draft(year)
        context = {
            'draft': draft,
        }
        return self.render_to_response(context)


class PlayerView(TemplateView):
    template_name = 'blingaleague/player.html'

    def get(self, request, player):
        player = Player(player)

        if not player.transactions_list:
            raise Http404("No history of player {}".format(player))

        context = {'player': player}
        return self.render_to_response(context)
