from django.conf.urls import url
from django.views.decorators.cache import cache_page

from .views import WeeklyScoresView, ExpectedWinsView, GameFinderView, SeasonFinderView

default_cache_timeout = 365 * 24 * 60 * 60

urlpatterns = [
    url(r'weekly_scores/$', cache_page(default_cache_timeout)(WeeklyScoresView.as_view()), name='blingalytics.weekly_scores'),
    url(r'expected_wins/$', cache_page(default_cache_timeout)(ExpectedWinsView.as_view()), name='blingalytics.expected_wins'),
    url(r'game_finder/$', cache_page(default_cache_timeout)(GameFinderView.as_view()), name='blingalytics.game_finder'),
    url(r'season_finder/$', cache_page(default_cache_timeout)(SeasonFinderView.as_view()), name='blingalytics.season_finder'),
]
