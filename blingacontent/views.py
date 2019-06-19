import csv

from django.views.generic import ListView, DetailView

from tagging.models import TaggedItem
from tagging.utils import parse_tag_input

from .forms import GazetteSearchForm
from .models import Gazette


class GazetteListView(ListView):
    model = Gazette
    form_class = GazetteSearchForm
    context_object_name = 'gazette_list'

    def parse_full_tag_input(self):
        full_tag_input = self.form.cleaned_data['tag']
        return parse_tag_input(full_tag_input)

    def parse_full_search_term(self):
        full_search_term = self.form.cleaned_data['search']
        return parse_tag_input(full_search_term)

    def get_queryset(self):
        queryset = Gazette.objects.filter(
            publish_flag=True,
        ).order_by(
            '-published_date',
            'headline',
        )

        self.form = self.form_class(self.request.GET)

        if self.form.is_valid():
            tags = self.parse_full_tag_input()
            if tags:
                all_tagged_ids = None

                for tag in tags:
                    tagged_ids = set(TaggedItem.objects.filter(
                        tag__name=tag,
                    ).values_list('object_id', flat=True))

                    if all_tagged_ids is None:
                        all_tagged_ids = tagged_ids
                    else:
                        all_tagged_ids.intersection_update(tagged_ids)

                if all_tagged_ids:
                    queryset = queryset.filter(pk__in=all_tagged_ids)
                else:
                    # if nothing is tagged, force no results
                    return queryset.none()

            search_terms = self.parse_full_search_term()
            for search_term in search_terms:
                if not search_term:
                    continue  # take care of extra spaces

                queryset = queryset.filter(body__icontains=search_term)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['form'] = self.form
        return context


class GazetteDetailView(DetailView):
    model = Gazette
    slug_url_kwarg = 'slug'
    query_pk_and_slug = True
