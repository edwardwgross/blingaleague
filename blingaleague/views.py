from django.views.generic import TemplateView

from .models import Standings

class HomeView(TemplateView):
    template_name = 'blingaleague/home.html'


class StandingsView(TemplateView):
    template_name = 'blingaleague/standings.html'

    def get(self, request, year, **kwargs):
        year = int(year)
        context = {
            'year': year,
            'standings': Standings(year=year),
        }
        return self.render_to_response(context)
