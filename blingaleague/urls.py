from django.conf.urls import patterns, url, include
from django.contrib import admin

from django.contrib.auth.views import login, logout

from .views import HomeView, TeamDetailsView, TeamVsTeamView,\
                   StandingsYearView, StandingsCurrentView, StandingsAllTimeView,\
                   GamesView, MatchupView, WeekView, TeamSeasonView


admin.autodiscover()

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

    (r'^blingalytics/', include('blingalytics.urls')),

    url(r'^login/$', login, {'template_name': 'blingaleague/login.html'}, name='login'),
    url(r'^logout/$', logout, name='logout'),
    url(r'^admin/', include(admin.site.urls)),
)

