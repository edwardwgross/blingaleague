from django.views.generic import ListView, DetailView

from .models import Gazette


class GazetteListView(ListView):
    model = Gazette
    context_object_name = 'gazette_list'
    ordering = ['-published_date', 'headline']


class GazetteDetailView(DetailView):
    model = Gazette
    slug_url_kwarg = 'slug'
    query_pk_and_slug = True
