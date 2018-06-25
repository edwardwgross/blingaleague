from django.conf import settings
from django.conf.urls import url
from django.views.decorators.cache import cache_page

from .views import GazetteListView, GazetteDetailView

default_cache_timeout = settings.PAGE_CACHE_DEFAULT_TIMEOUT

urlpatterns = [
    url(
        r'sanderson_gazette/$',
        cache_page(default_cache_timeout)(GazetteListView.as_view()),
        name='blingacontent.gazette_list',
    ),
    url(
        r'sanderson_gazette/(?P<slug>[-\w]+)/$',
        cache_page(default_cache_timeout)(GazetteDetailView.as_view()),
        name='blingacontent.gazette_detail',
    ),
]
