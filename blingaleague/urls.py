from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth.views import login, logout
from django.views.generic import RedirectView

from .views import HomeView, TeamDetailsView, TeamListView,\
                   SeasonListView, SingleSeasonView,\
                   MatchupView, WeekView, TeamSeasonView,\
                   TradeView


admin.autodiscover()

urlpatterns = [
    url(
        r'^$',
        HomeView.as_view(),
        name='blingaleague.home',
    ),
    url(
        r'^seasons/$',
        SeasonListView.as_view(),
        name='blingaleague.seasons',
    ),
    url(
        r'^season/(?P<year>\d{4})/$',
        SingleSeasonView.as_view(),
        name='blingaleague.single_season',
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
        r'^teams/$',
        TeamListView.as_view(),
        name='blingaleague.teams',
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
    url(
        r'^trade/(?P<trade>\d+)/$',
        TradeView.as_view(),
        name='blingaleague.trade',
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

    # more deprecated urls
    url(
        r'^standings/$',
        RedirectView.as_view(
            pattern_name='blingaleague.current_season',
            permanent=True,
        ),
    ),

    url(
        r'^standings/(?P<year>\d{4})/$',
        RedirectView.as_view(
            pattern_name='blingaleague.single_season',
            permanent=True,
        ),
    ),

    url(
        r'^season/all_time/$',
        RedirectView.as_view(
            pattern_name='blingaleague.teams',
            permanent=True,
        ),
    ),

    url(
        r'^standings/all_time/$',
        RedirectView.as_view(
            pattern_name='blingaleague.teams',
            permanent=True,
        ),
    ),

    url(
        r'^season/$',
        RedirectView.as_view(
            pattern_name='blingaleague.seasons',
            permanent=True,
        ),
    ),
    # end deprecated urls

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
