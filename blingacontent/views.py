from django.views.generic import ListView, DetailView

from .models import Gazette


class GazetteListView(ListView):
    model = Gazette
    context_object_name = 'gazette_list'
