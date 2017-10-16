import nvd3

from cached_property import cached_property

from collections import defaultdict

from django.core import urlresolvers
from django.http import HttpResponseForbidden
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from .models import Standings, Game, Member, TeamSeason, Week, Matchup


class HomeView(TemplateView):
    template_name = 'blingaleague/home.html'

    def get(self, request):
        standings = Standings()

        year, week = Game.objects.all().order_by('-year', '-week').values_list('year', 'week')[0]
        week = Week(year, week)

        context = {'standings': standings, 'week': week}

        return self.render_to_response(context)


class StandingsView(TemplateView):
    template_name = 'blingaleague/standings.html'

    @cached_property
    def links(self):
        links = []

        for year in sorted(set(Game.objects.all().values_list('year', flat=True))):
            link_data = {'text': year, 'href': None}
            if year != self.standings.year:
                link_data['href'] = urlresolvers.reverse_lazy('blingaleague.standings_year', args=(year,))
            links.append(link_data)

        all_time_url = urlresolvers.reverse_lazy('blingaleague.standings_all_time')
        including_playoffs_url = "%s?include_playoffs" % all_time_url

        if self.standings.all_time:
            if self.standings.include_playoffs:
                including_playoffs_url = None
            else:
                all_time_url = None

        links.extend([
            {'text': 'All-time', 'href': all_time_url},
            {'text': '(including playoffs)', 'href': including_playoffs_url},
        ])

        return links

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



class StandingsCurrentView(StandingsView):
    sub_templates = (
        #'blingaleague/expected_win_distribution_standings.html',
    )

    def get(self, request):
        self.standings = Standings()
        context = {
            'standings': self.standings,
            'links': self.links,
            #'sub_templates': self.sub_templates,
            #'expected_win_distribution_graph': self._expected_win_distribution_graph(self.standings.table),
        }
        return self.render_to_response(context)


class StandingsYearView(StandingsView):
    sub_templates = (
        #'blingaleague/expected_win_distribution_standings.html',
    )

    def get(self, request, year):
        self.standings = Standings(year=int(year))
        context = {
            'standings': self.standings,
            'links': self.links,
            #'sub_templates': self.sub_templates,
            #'expected_win_distribution_graph': self._expected_win_distribution_graph(self.standings.table),
        }
        return self.render_to_response(context)


class StandingsAllTimeView(StandingsView):

    def get(self, request):
        include_playoffs = 'include_playoffs' in request.GET
        self.standings = Standings(all_time=True, include_playoffs=include_playoffs)
        context = {'standings': self.standings, 'links': self.links}
        return self.render_to_response(context)


class GamesView(TemplateView):
    template_name = 'blingaleague/games.html'
    sub_templates = []

    def _context(self, base_object):
        return {'base_object': base_object, 'sub_templates': self.sub_templates}


class MatchupView(GamesView):

    def get(self, request, team1, team2):
        base_object = Matchup(team1, team2)
        context = self._context(base_object)
        return self.render_to_response(context)


class WeekView(GamesView):

    def get(self, request, year, week):
        base_object = Week(year, week)
        context = self._context(base_object)
        return self.render_to_response(context)


class TeamSeasonView(GamesView):
    sub_templates = (
        'blingaleague/expected_win_distribution_team.html',
        # TODO enable when more performant sub_templates 'blingaleague/similar_seasons.html',
    )

    def _expected_win_distribution_graph(self, expected_win_distribution):
        expected_win_distribution = sorted(expected_win_distribution.items())
        x_data = map(lambda x: x[0], expected_win_distribution)
        y_data = map(lambda x: float(x[1]), expected_win_distribution)

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
        context['expected_win_distribution_graph'] = self._expected_win_distribution_graph(base_object.expected_win_distribution)
        return self.render_to_response(context)


class TeamDetailsView(TemplateView):
    template_name = 'blingaleague/team_details.html'

    def get(self, request, team):
        team = Member.objects.get(id=team)
        context = {'team': team}
        return self.render_to_response(context)


class TeamVsTeamView(TemplateView):
    template_name = 'blingaleague/team_vs_team.html'

    def get(self, request):
        matchups = []

        teams = Member.objects.all().order_by('defunct', 'first_name', 'last_name')

        grid = [{'team': team, 'matchups': Matchup.get_all_for_team(team.id)} for team in teams]

        context = {'grid': grid, 'teams': teams}

        return self.render_to_response(context)


