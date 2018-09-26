import csv

from django.views.generic import ListView, DetailView

from .forms import GazetteSearchForm
from .models import Gazette


class GazetteListView(ListView):
    model = Gazette
    form_class = GazetteSearchForm
    context_object_name = 'gazette_list'

    def parse_full_search_term(self):
        full_search_term = self.form.cleaned_data['search']
        parsed_terms = list(csv.reader([full_search_term], delimiter=' '))[0]
        return filter(lambda x: x, parsed_terms)

    def get_queryset(self):
        queryset = Gazette.objects.filter(publish_flag=True)

        self.form = self.form_class(self.request.GET)
        if self.form.is_valid():
            full_filter = None

            for search_part in self.parse_full_search_term():
                if not search_part:
                    continue  # take care of extra spaces

                queryset = queryset.filter(body__icontains=search_part)

        queryset = queryset.order_by('-published_date', 'headline')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['form'] = self.form
        return context


class GazetteDetailView(DetailView):
    model = Gazette
    slug_url_kwarg = 'slug'
    query_pk_and_slug = True
