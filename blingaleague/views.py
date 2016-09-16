from django.views.generic import View, TemplateView

from .models import Standings

class Home(TemplateView):
    template_name = 'blingaleague/home.html'


class Standings(TemplateView):
    template_name = 'blingaleague/standings.html'

    def get(self, request, year):
        standings = Standings(year)

        context = {
            'year': year,
            'standings': Standings,
        }

        return self.render_to_response(context)
