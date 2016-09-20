from collections import defaultdict

from django.core import urlresolvers
from django.db.models import Q
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from .models import Standings, Game, Member

class HomeView(TemplateView):
    template_name = 'blingaleague/home.html'

    def get(self, request):
        standings = Standings()

        context = {'standings': standings}

        return self.render_to_response(context)


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


class GamesView(TemplateView):
    template_name = 'blingaleague/games.html'

    def get(self, request):
        games = Game.objects.all()

        headline = 'Games'

        teams = [Member.objects.get(pk=team_id) for team_id in request.GET.getlist('team')]
        teams = sorted(teams, key=lambda x: x.full_name)[:2]  # never want more than 2

        years = [int(year) for year in request.GET.getlist('year')]
        weeks = [int(week) for week in request.GET.getlist('week')]

        for team in teams:
            games = games.filter(Q(winner=team) | Q(loser=team))

        if len(teams) > 1:
            # we're doing a matchup, so don't allow any date restrictions
            headline = "%s played between %s and %s" % (headline, teams[0], teams[1])
        else:
            if teams:
                if years:
                    games = games.filter(year__in=years)
                if weeks:
                    games = games.filter(week__in=weeks)
            else:
                # if we didn't give a team filter, limit to the most recent one year and week specified
                if years:
                    year = years[-1]
                else:
                    year = Game.objects.all().order_by('-year').values_list('year', flat=True)[0]

                if weeks:
                    week = weeks[-1]
                else:
                    week = Game.objects.filter(year=year).order_by('-week').values_list('week', flat=True)[0]

                games = games.filter(year=year, week=week)

        games = games.order_by('year', 'week', 'winner_score', 'loser_score')

        context = {'games': games}

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
