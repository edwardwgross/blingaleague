from django.views.generic import ListView, DetailView

from .forms import GazetteSearchForm
from .models import Gazette


class GazetteListView(ListView):
    model = Gazette
    form_class = GazetteSearchForm
    context_object_name = 'gazette_list'

    def get_queryset(self):
        queryset = Gazette.objects.filter(publish_flag=True)

        self.form = self.form_class(self.request.GET)
        if self.form.is_valid():
            queryset = queryset.filter(
                body__icontains=self.form.cleaned_data['search']
            )

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
