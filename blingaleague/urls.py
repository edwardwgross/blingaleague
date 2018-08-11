from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth.views import login, logout
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

from .views import HomeView, TeamDetailsView,\
                   StandingsYearView, StandingsCurrentView, StandingsAllTimeView,\
                   MatchupView, WeekView, TeamSeasonView


admin.autodiscover()

urlpatterns = [
    url(
        r'^$',
        HomeView.as_view(),
        name='blingaleague.home',
    ),
    url(
        r'^standings/$',
        StandingsCurrentView.as_view(),
        name='blingaleague.standings',
    ),
    url(
        r'^standings/(?P<year>\d{4})/$',
        StandingsYearView.as_view(),
        name='blingaleague.standings_year',
    ),
    url(
        r'^standings/all_time/$',
        StandingsAllTimeView.as_view(),
        name='blingaleague.standings_all_time',
    ),
    url(
        r'^matchup/(?P<team1>\d+)/(?P<team2>\d+)/$',
        MatchupView.as_view(),
        name='blingaleague.matchup',
    ),
    url(
        r'^week/(?P<year>\d{4})/(?P<week>\d+)/$',
        WeekView.as_view(),
        name='blingaleague.week',
    ),
    url(
        r'^team/(?P<team>\d+)/$',
        TeamDetailsView.as_view(),
        name='blingaleague.team',
    ),
    url(
        r'^team/(?P<team>\d+)/(?P<year>\d{4})/$',
        TeamSeasonView.as_view(),
        name='blingaleague.team_season',
    ),

    # done this way so old links still work, even though this
    # view was moved to the blingalytics app
    url(
        r'^team_vs_team/$',
        RedirectView.as_view(
            pattern_name='blingalytics.team_vs_team',
            permanent=True,
        )
    ),

    url(
        r'^blingalytics/',
        include('blingalytics.urls'),
    ),

    url(
        r'^',
        include('blingacontent.urls'),
    ),

    url(
        r'^auth/',
        include('social_django.urls', namespace='social'),
    ),
    url(
        r'^login/$',
        login,
        {'template_name': 'blingaleague/login.html'},
        name='login',
    ),
    url(
        r'^logout/$',
        logout,
        name='logout',
    ),
    url(
        r'^admin/',
        include(admin.site.urls),
    ),
]
