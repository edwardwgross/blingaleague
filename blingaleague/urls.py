from django.conf.urls import patterns, url

from .views import Home, Standings

urlpatterns = patterns('',
    url(r'^$', Home.as_view(), name='blingaleague.home'),
    url(r'^standings/(?P<year>)\d+/$', Standings.as_view(), name='blingaleague.standings'),
)
