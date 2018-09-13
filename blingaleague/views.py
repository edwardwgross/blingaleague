import nvd3

from cached_property import cached_property

from django.core import urlresolvers
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

from blingacontent.models import Gazette

from .models import Standings, Game, Member, TeamSeason, Week, Matchup, Year


class HomeView(TemplateView):
    template_name = 'blingaleague/home.html'

    def get(self, request):
        standings = Standings.latest()

        week = Week.latest()

        gazette = Gazette.latest()

        context = {'standings': standings, 'week': week, 'gazette': gazette}

        return self.render_to_response(context)


class SeasonView(TemplateView):
    template_name = 'blingaleague/season.html'

    @cached_property
    def season_links(self):
        season_links = []

        for year in sorted(Year.all()):
            link_data = {'text': year, 'href': None}
            if year != self.standings.year:
                link_data['href'] = urlresolvers.reverse_lazy(
                    'blingaleague.single_season',
                    args=(year,),
                )
            season_links.append(link_data)

        all_time_url = urlresolvers.reverse_lazy('blingaleague.all_time')
        including_playoffs_url = "{}?include_playoffs".format(all_time_url)

        if self.standings.all_time:
            if self.standings.include_playoffs:
                including_playoffs_url = None
            else:
                all_time_url = None

        season_links.extend([
            {'text': 'All-time', 'href': all_time_url},
            {'text': '(including playoffs)', 'href': including_playoffs_url},
        ])

        return season_links

    @cached_property
    def week_links(self):
        # only applies for single-season view
        return []

    def _expected_win_distribution_graph(self, team_seasons):
        graph = nvd3.lineChart(
            name='expected_wins',
            width=600,
            height=400,
            y_axis_format='%',
        )

        x_data = None

        for team_season in team_seasons:
            expected_win_distribution = sorted(team_season.expected_win_distribution.items())
            y_data = map(lambda x: float(x[1]), expected_win_distribution)
            if x_data is None:
                x_data = map(lambda x: x[0], expected_win_distribution)

            graph.add_serie(x=x_data, y=y_data, name=team_season.team.nickname)

        graph.buildcontent()
        graph.buildhtml()

        return graph


class CurrentSeasonView(SeasonView):

    def get(self, request):
        redirect_url = urlresolvers.reverse_lazy('blingaleague.single_season', args=(Year.max(),))
        return HttpResponseRedirect(redirect_url)


class SingleSeasonView(SeasonView):

    @cached_property
    def week_links(self):
        week_links = []

        weeks_with_games = set(
            Game.objects.filter(
                year=self.standings.year,
            ).values_list(
                'week',
                flat=True,
            ),
        )

        for week in sorted(weeks_with_games):
            link_data = {
                'text': week,
                'href': urlresolvers.reverse_lazy(
                    'blingaleague.week',
                    args=(self.standings.year, week,),
                ),
            }
            week_links.append(link_data)

        return week_links

    def get(self, request, year):
        self.standings = Standings(year=int(year))
        context = {
            'standings': self.standings,
            'season_links': self.season_links,
            'week_links': self.week_links,
        }
        return self.render_to_response(context)


class AllTimeView(SeasonView):

    def get(self, request):
        include_playoffs = 'include_playoffs' in request.GET
        self.standings = Standings(all_time=True, include_playoffs=include_playoffs)
        context = {
            'standings': self.standings,
            'season_links': self.season_links,
            'week_links': self.week_links,
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

    def get(self, request, team1, team2):
        base_object = Matchup(team1, team2)
        context = self._context(base_object)
        return self.render_to_response(context)


class WeekView(GamesView):
    games_sub_template = 'blingaleague/weekly_games.html'

    def get(self, request, year, week):
        base_object = Week(year, week)
        context = self._context(base_object)
        return self.render_to_response(context)


class TeamSeasonView(GamesView):
    # would like to include 'blingaleague/similar_seasons.html',
    # but it's a performance nightmare
    pre_games_sub_templates = (
        'blingaleague/expected_win_distribution_team.html',
    )
    post_games_sub_templates = (
        'blingaleague/similar_seasons.html',
    )
    games_sub_template = 'blingaleague/team_season_games.html'

    def _expected_win_distribution_graph(self, expected_win_distribution):
        expected_win_distribution = sorted(expected_win_distribution.items())
        x_data = list(map(lambda x: x[0], expected_win_distribution))
        y_data = list(map(lambda x: float(x[1]), expected_win_distribution))

        graph = nvd3.discreteBarChart(
            name='expected_win_distribution',
            width=600,
            height=200,
            y_axis_format='%',
        )

        graph.add_serie(x=x_data, y=y_data)

        graph.buildcontent()
        graph.buildhtml()

        return graph

    def get(self, request, team, year):
        base_object = TeamSeason(team, year, include_playoffs=True)
        context = self._context(base_object)
        context['expected_win_distribution_graph'] = self._expected_win_distribution_graph(
            base_object.expected_win_distribution,
        )
        return self.render_to_response(context)


class TeamDetailsView(TemplateView):
    template_name = 'blingaleague/team_details.html'

    def get(self, request, team):
        team = Member.objects.get(id=team)
        context = {'team': team}
        return self.render_to_response(context)
