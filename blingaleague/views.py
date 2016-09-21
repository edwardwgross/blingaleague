from collections import defaultdict

from django.core import urlresolvers
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from .models import Standings, Game, Member, TeamRecord, Week, Matchup

class HomeView(TemplateView):
    template_name = 'blingaleague/home.html'

    def get(self, request):
        standings = Standings()

        context = {'standings': standings}

        return self.render_to_response(context)


class StandingsView(TemplateView):
    template_name = 'blingaleague/standings.html'

    def links(self):
        links = []

        for season in sorted(set(Game.objects.all().values_list('year', flat=True))):
            link_data = {'text': season, 'href': None}
            if season != self.standings.year:
                link_data['href'] = urlresolvers.reverse_lazy('blingaleague.standings_year', args=(season,))
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
        self.standings = Standings(year=year)
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
        base_object = TeamRecord(team, [year])
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
        stats = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'losses': 0}))
        # ex: stats['Allen']['Matt'] = {'wins': 1, 'losses': 3}

        for game in Game.objects.all():
            stats[game.winner][game.loser]['wins'] += 1
            stats[game.loser][game.winner]['losses'] += 1

        all_teams = sorted(stats.keys(), key=lambda x: x.full_name)
        grid = [['W\L'] + all_teams]

        for team_a in all_teams:
            row = [team_a]
            for team_b in all_teams:
                if team_a == team_b:
                    row.append('')
                else:
                    wins = stats[team_a][team_b]['wins']
                    losses = stats[team_a][team_b]['losses']
                    row.append("%s-%s" % (wins, losses))

            grid.append(row)

        context = {'grid': grid}

        return self.render_to_response(context)


class AddGameResultView(CreateView):
    model = Game
    fields = ['year', 'week', 'winner', 'winner_score', 'loser', 'loser_score']
    success_url = urlresolvers.reverse_lazy('blingaleague.add_game_result')
