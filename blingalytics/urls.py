from django.conf.urls import url
from django.views.generic import RedirectView

from .views import WeeklyScoresView, ExpectedWinsView, \
                   GameFinderView, SeasonFinderView, \
                   TopSeasonsView, TeamVsTeamView, \
                   BeltHolderView, TradeFinderView, \
                   KeeperFinderView, DraftPickFinderView, \
                   ShortUrlView, PlayoffOddsView

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
        r'keeper_finder/$',
        KeeperFinderView.as_view(),
        name='blingalytics.keeper_finder',
    ),
    url(
        r'draft_pick_finder/$',
        DraftPickFinderView.as_view(),
        name='blingalytics.draft_pick_finder',
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
    url(
        r'u/(?P<short_url>[\w]+)/$',
        ShortUrlView.as_view(),
        name='blingalytics.short_url',
    ),
    # XXX bring this back someday?
    #url(
    #    r'playoff_odds/$',
    #    PlayoffOddsView.as_view(),
    #    name='blingalytics.playoff_odds',
    #),

    # deprecated urls
    url(
        r'^glossary/$',
        RedirectView.as_view(
            pattern_name='blingaleague.glossary',
            permanent=True,
        ),
    ),
]
