from cached_property import cached_property

from django.core import urlresolvers
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

from blingacontent.models import Gazette

from .models import Standings, Game, Member, \
                    TeamSeason, Week, Matchup, Year, \
                    REGULAR_SEASON_WEEKS


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
        standings_kwargs = {
            'year': int(year),
        }

        week_max = None
        if 'week_max' in request.GET:
            try:
                week_max = int(request.GET.get('week_max', REGULAR_SEASON_WEEKS))
                standings_kwargs['week_max'] = week_max
            except ValueError:
                # ignore if user passed in a non-int
                pass

        self.standings = Standings(**standings_kwargs)

        context = {
            'standings': self.standings,
            'season_links': self.season_links,
            'week_links': self.week_links,
            'week_max': week_max,
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
        context = self._context(Matchup(team1, team2))
        return self.render_to_response(context)


class WeekView(GamesView):
    games_sub_template = 'blingaleague/weekly_games.html'

    def get(self, request, year, week):
        year = int(year)
        week = int(week)

        context = self._context(Week(year, week))

        context['standings'] = Standings(
            year,
            week_max=week,
        )

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

    def get(self, request, team, year):
        context = self._context(
            TeamSeason(team, year, include_playoffs=True),
        )
        return self.render_to_response(context)


class TeamDetailsView(TemplateView):
    template_name = 'blingaleague/team_details.html'

    def get(self, request, team):
        team = Member.objects.get(id=team)
        context = {'team': team}
        return self.render_to_response(context)
