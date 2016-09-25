from collections import defaultdict

from django.core import urlresolvers
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

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


class StandingsCurrentView(StandingsView):

    def get(self, request):
        self.standings = Standings()
        context = {'standings': self.standings, 'links': self.links()}
        return self.render_to_response(context)

class StandingsYearView(StandingsView):

    def get(self, request, year):
        self.standings = Standings(year=int(year))
        context = {'standings': self.standings, 'links': self.links()}
        return self.render_to_response(context)


class StandingsAllTimeView(StandingsView):

    def get(self, request):
        include_playoffs = 'include_playoffs' in request.GET
        self.standings = Standings(all_time=True, include_playoffs=include_playoffs)
        context = {'standings': self.standings, 'links': self.links()}
        return self.render_to_response(context)


class GamesView(TemplateView):
    template_name = 'blingaleague/games.html'


class MatchupView(GamesView):

    def get(self, request, team1, team2):
        base_object = Matchup(team1, team2)
        context = {'base_object': base_object}
        return self.render_to_response(context)


class WeekView(GamesView):

    def get(self, request, year, week):
        base_object = Week(year, week)
        context = {'base_object': base_object}
        return self.render_to_response(context)


class TeamSeasonView(GamesView):

    def get(self, request, team, year):
        base_object = TeamSeason(team, year, include_playoffs=True)
        context = {'base_object': base_object}
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

        teams = Member.objects.all().order_by('first_name', 'last_name')

        grid = [{'team': team, 'matchups': Matchup.get_all_for_team(team.id)} for team in teams]

        context = {'grid': grid, 'teams': teams}

        return self.render_to_response(context)


class AddGameResultView(CreateView):
    model = Game
    fields = ['year', 'week', 'winner', 'winner_score', 'loser', 'loser_score', 'notes']
    success_url = urlresolvers.reverse_lazy('blingaleague.add_game_result')
