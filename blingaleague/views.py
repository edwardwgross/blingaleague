from django.views.generic import TemplateView

from .models import Standings

class HomeView(TemplateView):
    template_name = 'blingaleague/home.html'


class StandingsView(TemplateView):
    template_name = 'blingaleague/standings.html'

    def get(self, request):
        standings_kwargs = {}

        if 'year' in request.GET:
            standings_kwargs['year'] = int(request.GET['year'])

        for kwarg in ('all_time', 'include_playoffs'):
            if kwarg in request.GET:
                standings_kwargs[kwarg] = True

        context = {'standings': Standings(**standings_kwargs)}

        return self.render_to_response(context)

