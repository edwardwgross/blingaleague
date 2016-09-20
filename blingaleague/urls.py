from django.conf.urls import patterns, url

from .views import HomeView, StandingsView

urlpatterns = patterns('',
    url(r'^$', HomeView.as_view(), name='blingaleague.home'),
    url(r'^standings/$', StandingsView.as_view(), name='blingaleague.standings'),
)
