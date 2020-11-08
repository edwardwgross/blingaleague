from collections import defaultdict

from django.contrib.humanize.templatetags.humanize import ordinal, intcomma
from django.views.generic import TemplateView

from blingacontent.models import Gazette

from .models import Season, Game, Member, \
                    TeamSeason, Week, Matchup, \
                    Trade, \
                    REGULAR_SEASON_WEEKS, BLINGABOWL_WEEK, \
                    PLAYOFF_TEAMS
from .utils import line_graph_html, bar_graph_html


class HomeView(TemplateView):
    template_name = 'blingaleague/home.html'

    def get(self, request):
        context = {
            'season': Season.latest(),
            'week': Week.latest(),
            'gazette': Gazette.latest(),
            'trades': Trade.most_recent(),
        }
        return self.render_to_response(context)


class SeasonListView(TemplateView):
    template_name = 'blingaleague/season_list.html'

    def get(self, request):
        context = {
            'season_list': sorted(Season.all(), reverse=True),
        }
        return self.render_to_response(context)


class SingleSeasonView(TemplateView):
    template_name = 'blingaleague/season.html'

    def get(self, request, year):
        season_kwargs = {
            'year': int(year),
        }

        week_max = None
        hide_playoff_finish = False
        if 'week_max' in request.GET:
            try:
                week_max = int(request.GET.get('week_max', REGULAR_SEASON_WEEKS))
                season_kwargs['week_max'] = week_max
                hide_playoff_finish = week_max < BLINGABOWL_WEEK
            except ValueError:
                # ignore if user passed in a non-int
                pass

        self.season = Season(**season_kwargs)

        weeks_with_games = sorted(set(
            Game.objects.filter(
                year=self.season.year,
            ).values_list(
                'week',
                flat=True,
            ),
        ))

        context = {
            'season': self.season,
            'week_max': week_max,
            'weeks_with_games': weeks_with_games,
            'hide_playoff_finish': hide_playoff_finish,
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

        context['season'] = Season(
            year=year,
            week_max=week,
        )

        context['hide_playoff_finish'] = week < BLINGABOWL_WEEK

        return self.render_to_response(context)


class TeamListView(TemplateView):
    template_name = 'blingaleague/team_list.html'

    def _team_graph_list(self):
        graph_attrs = [
            # (graph title, TeamSeason attribute, value format)
            ('Wins', 'win_count', '{:.0f}'),
            ('Points', 'points', '{:.2f}'),
            ('Expected Wins', 'expected_wins', '{:.2f}'),
        ]

        graph_list = []

        years = [s.year for s in sorted(Season.all()) if not s.is_partial]
        team_list = Member.objects.all()

        for title, attr, value_format in graph_attrs:
            custom_options = {
                'title': title,
                'width': 800,
                'value_formatter': lambda x: intcomma(value_format.format(x)),
                'truncate_label': 4,
            }

            team_series = []
            for team in sorted(team_list, key=lambda x: x.nickname):
                team_data = []
                for year in years:
                    team_season = TeamSeason(team.id, year)
                    if team_season.games:
                        value = getattr(team_season, attr)
                        if value_format != 'i':
                            value = float(value)
                        team_data.append(value)
                    else:
                        team_data.append(None)

                team_series.append((team.nickname, team_data))

            graph_html = line_graph_html(
                years,  # x_data
                team_series,  # y_series
                **custom_options,
            )

            graph_list.append(graph_html)

        return graph_list

    def get(self, request):
        context = {
            'team_list': Member.objects.all(),
            'include_playoffs': 'include_playoffs' in request.GET,
            'graph_list': self._team_graph_list(),
        }
        return self.render_to_response(context)


class TeamSeasonView(GamesView):
    pre_games_sub_templates = (
        'blingaleague/expected_win_distribution_team.html',
    )
    post_games_sub_templates = (
        'blingaleague/team_season_keepers.html',
        'blingaleague/team_season_trades.html',
        'blingaleague/team_season_rank_by_week.html',
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

        graph_html = bar_graph_html(
            wins, # x_data
            [('', odds)], # y_series
            **custom_options,
        )

        return graph_html

    def _rank_by_week_graph(self, team_season):
        weeks = sorted(team_season.rank_by_week.keys())
        rank_series = defaultdict(list)

        total_teams = len(Season(team_season.year).standings_table)

        for week in weeks:
            ranks = team_season.rank_by_week[week]
            for name, value in ranks.items():
                rank_series[name.title()].append(total_teams - value)

        custom_options = {
            'title': 'Rank by Week',
            'width': 800,
            'x_title': 'Week',
            'min_scale': total_teams - 1,
            'max_scale': total_teams - 1,
            'range': (0, total_teams - 1),
            'y_labels_major': [total_teams - PLAYOFF_TEAMS],
            'value_formatter': lambda x: ordinal(total_teams - x),
        }

        graph_html = line_graph_html(
            weeks, # x_data
            sorted(rank_series.items()), # y_series
            **custom_options,
        )

        return graph_html

    def get(self, request, team, year):
        week_max = None
        if 'week_max' in request.GET:
            try:
                week_max = min(
                    int(request.GET.get('week_max', REGULAR_SEASON_WEEKS)),
                    REGULAR_SEASON_WEEKS,
                )
            except ValueError:
                # ignore if user passed in a non-int
                pass


        team_season = TeamSeason(
            team,
            year,
            include_playoffs=True,
            week_max=week_max,
        )

        context = self._context(team_season)
        context['expected_win_distribution_graph_html'] = self._expected_win_distribution_graph(team_season)
        context['rank_by_week_graph_html'] = self._rank_by_week_graph(team_season)

        return self.render_to_response(context)


class TeamDetailsView(TemplateView):
    template_name = 'blingaleague/team_details.html'

    def get(self, request, team):
        team = Member.objects.get(id=team)
        context = {'team': team}
        return self.render_to_response(context)


class TradeView(TemplateView):
    template_name = 'blingaleague/trade_base.html'

    def get(self, request, trade):
        trade = Trade.objects.get(id=trade)
        context = {'trade': trade}
        return self.render_to_response(context)
