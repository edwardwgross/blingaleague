from django.conf.urls import url

from .views import GazetteListView, GazetteDetailView

urlpatterns = [
    url(
        r'sanderson_gazette/$',
        GazetteListView.as_view(),
        name='blingacontent.gazette_list',
    ),
    url(
        r'sanderson_gazette/(?P<slug>[-\w]+)/$',
        GazetteDetailView.as_view(),
        name='blingacontent.gazette_detail',
    ),
]
