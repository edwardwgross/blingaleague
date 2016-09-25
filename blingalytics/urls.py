from django.conf.urls import patterns, url

from .views import WeeklyScoresView, ExpectedWinsView, GameFinderView


urlpatterns = patterns('',
    url(r'weekly_scores/$', WeeklyScoresView.as_view(), name='blingalytics.weekly_scores'),
    url(r'expected_wins/$', ExpectedWinsView.as_view(), name='blingalytics.expected_wins'),
    url(r'game_finder/$', GameFinderView.as_view(), name='blingalytics.game_finder'),
)

