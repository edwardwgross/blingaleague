from django.conf.urls import url

from .views import WeeklyScoresView, ExpectedWinsView, \
                   GameFinderView, SeasonFinderView, \
                   TopSeasonsView, TeamVsTeamView, \
                   BeltHolderView, TradeFinderView

urlpatterns = [
    url(
        r'team_vs_team/$',
        TeamVsTeamView.as_view(),
        name='blingalytics.team_vs_team',
    ),
    url(
        r'weekly_scores/$',
        WeeklyScoresView.as_view(),
        name='blingalytics.weekly_scores',
    ),
    url(
        r'expected_wins/$',
        ExpectedWinsView.as_view(),
        name='blingalytics.expected_wins',
    ),
    url(
        r'game_finder/$',
        GameFinderView.as_view(),
        name='blingalytics.game_finder',
    ),
    url(
        r'season_finder/$',
        SeasonFinderView.as_view(),
        name='blingalytics.season_finder',
    ),
    url(
        r'trade_finder/$',
        TradeFinderView.as_view(),
        name='blingalytics.trade_finder',
    ),
    url(
        r'top_seasons/$',
        TopSeasonsView.as_view(),
        name='blingalytics.top_seasons',
    ),
    url(
        r'belt_holders/$',
        BeltHolderView.as_view(),
        name='blingalytics.belt_holders',
    ),
]
