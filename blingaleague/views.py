import pygal

from django.views.generic import TemplateView

from blingacontent.models import Gazette

from .models import Season, Game, Member, \
                    TeamSeason, Week, Matchup, \
                    Trade, \
                    REGULAR_SEASON_WEEKS, BLINGABOWL_WEEK


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

    def _team_graph_lists(self):
        graph_attrs = [
            # (graph title, TeamSeason attribute, y_axis_format)
            ('Wins', 'win_count', '{:.0f}'),
            ('Points', 'points', '{:.2f}'),
            ('Expected Wins', 'expected_wins', '{:.2f}'),
        ]

        graph_list = []

        years = [s.year for s in sorted(Season.all()) if not s.is_partial]
        team_list = Member.objects.all()

        for title, attr, y_format in graph_attrs:
            graph = pygal.Line(
                title=title,
                width=800,
                height=400,
                margin=0,
                max_scale=6,
                value_formatter=lambda x: y_format.format(x),
                js=[],
            )

            graph.x_labels = years

            for team in sorted(team_list, key=lambda x: x.nickname):
                y_data = []
                for year in years:
                    team_season = TeamSeason(team.id, year)
                    if team_season.games:
                        y_value = getattr(team_season, attr)
                        if y_format != 'i':
                            y_value = float(y_value)
                        y_data.append(y_value)
                    else:
                        y_data.append(None)

                graph.add(
                    team.nickname,
                    y_data,
                )

            graph_list.append({
                'title': title,
                'html': graph.render(),
            })


        return graph_list

    def get(self, request):
        context = {
            'team_list': Member.objects.all(),
            'include_playoffs': 'include_playoffs' in request.GET,
            'graph_list': self._team_graph_lists(),
        }
        return self.render_to_response(context)


class TeamSeasonView(GamesView):
    pre_games_sub_templates = (
        'blingaleague/expected_win_distribution_team.html',
    )
    post_games_sub_templates = (
        'blingaleague/team_season_keepers.html',
        'blingaleague/team_season_trades.html',
        'blingaleague/similar_seasons.html',
    )
    games_sub_template = 'blingaleague/team_season_games.html'

    def _expected_win_distribution_graph(self, team_season):
        expected_win_distribution = sorted(team_season.expected_win_distribution.items())
        x_data = list(map(lambda x: x[0], expected_win_distribution))
        y_data = list(map(lambda x: float(x[1]), expected_win_distribution))

        graph = pygal.Bar(
            width=600,
            height=200,
            margin=0,
            show_legend=False,
            max_scale=6,
            value_formatter=lambda x: "{:.0f}%".format(100 * x),
            js=[],
        )

        graph.x_labels = x_data
        graph.add('', y_data)

        return graph.render()

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
