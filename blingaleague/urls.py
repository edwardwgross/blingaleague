from django.conf.urls import patterns, url

from .views import HomeView, TeamDetailsView, TeamVsTeamView, AddGameResultView,\
                   StandingsYearView, StandingsCurrentView, StandingsAllTimeView,\
                   GamesView, MatchupView, WeekView, TeamSeasonView

urlpatterns = patterns('',
    url(r'^$', HomeView.as_view(), name='blingaleague.home'),
    url(r'^standings/$', StandingsCurrentView.as_view(), name='blingaleague.standings'),
    url(r'^standings/(?P<year>\d{4})/$', StandingsYearView.as_view(), name='blingaleague.standings_year'),
    url(r'^standings/all_time/$', StandingsAllTimeView.as_view(), name='blingaleague.standings_all_time'),
    url(r'^matchup/(?P<team1>\d+)/(?P<team2>\d+)/$', MatchupView.as_view(), name='blingaleague.matchup'),
    url(r'^week/(?P<year>\d{4})/(?P<week>\d+)/$', WeekView.as_view(), name='blingaleague.week'),
    url(r'^team/(?P<team>\d+)/$', TeamDetailsView.as_view(), name='blingaleague.team'),
    url(r'^team/(?P<team>\d+)/(?P<year>\d{4})/$', TeamSeasonView.as_view(), name='blingaleague.team_season'),
    url(r'^team_vs_team/$', TeamVsTeamView.as_view(), name='blingaleague.team_vs_team'),
    url(r'^add_game_result/$', AddGameResultView.as_view(), name='blingaleague.add_game_result'),
)

