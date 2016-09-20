from django.conf.urls import patterns, url

from .views import HomeView, StandingsView, TeamVsTeamView, AddGameResultView

urlpatterns = patterns('',
    url(r'^$', HomeView.as_view(), name='blingaleague.home'),
    url(r'^standings/$', StandingsView.as_view(), name='blingaleague.standings'),
    url(r'^team_vs_team/$', TeamVsTeamView.as_view(), name='blingaleague.team_vs_team'),
    url(r'^add_game_result/$', AddGameResultView.as_view(), name='blingaleague.add_game_result'),
)
