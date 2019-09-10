from django.views.generic import TemplateView

from blingacontent.models import Gazette

from .models import Season, Game, Member, \
                    TeamSeason, Week, Matchup, \
                    REGULAR_SEASON_WEEKS


class HomeView(TemplateView):
    template_name = 'blingaleague/home.html'

    def get(self, request):
        context = {
            'season': Season.latest(),
            'week': Week.latest(),
            'gazette': Gazette.latest(),
        }
        return self.render_to_response(context)


class SeasonListView(TemplateView):
    template_name = 'blingaleague/season_list.html'

    def get(self, request):
        context = {
            'season_list': sorted(Season.all(), reverse=True),
        }
        return self.render_to_response(context)


class SeasonView(TemplateView):
    template_name = 'blingaleague/season.html'


class SingleSeasonView(SeasonView):

    def get(self, request, year):
        season_kwargs = {
            'year': int(year),
        }

        week_max = None
        if 'week_max' in request.GET:
            try:
                week_max = int(request.GET.get('week_max', REGULAR_SEASON_WEEKS))
                season_kwargs['week_max'] = week_max
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
        }

        return self.render_to_response(context)


class AllTimeStandingsView(SeasonView):

    def get(self, request):
        include_playoffs = 'include_playoffs' in request.GET
        self.season = Season(all_time=True, include_playoffs=include_playoffs)
        context = {
            'season': self.season,
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
    post_games_sub_templates = (
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
