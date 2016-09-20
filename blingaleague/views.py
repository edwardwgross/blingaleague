from collections import defaultdict

from django.views.generic import TemplateView

from .models import Standings, Game

class HomeView(TemplateView):
    template_name = 'blingaleague/home.html'


class StandingsView(TemplateView):
    template_name = 'blingaleague/standings.html'

    def get(self, request):
        standings_kwargs = {}

        if 'year' in request.GET:
            standings_kwargs['year'] = int(request.GET['year'])

        for kwarg in ('all_time', 'include_playoffs'):
            if kwarg in request.GET:
                standings_kwargs[kwarg] = True

        standings = Standings(**standings_kwargs)

        links = []
        for season in sorted(set(Game.objects.all().values_list('year', flat=True))):
            link_data = {'text': season, 'args': None}
            if season != standings.year:
                link_data['args'] = "year=%s" % season
            links.append(link_data)

        if standings.all_time and standings.include_playoffs:
            links.extend([
                {'text': 'All-time', 'args': 'all_time'},
                {'text': '(including playoffs)', 'args': None},
            ])
        elif standings.all_time:
            links.extend([
                {'text': 'All-time', 'args': None},
                {'text': '(including playoffs)', 'args': 'all_time&include_playoffs'},
            ])
        else:
            links.extend([
                {'text': 'All-time', 'args': 'all_time'},
                {'text': '(including playoffs)', 'args': 'all_time&include_playoffs'},
            ])


        context = {'standings': standings, 'links': links}

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


