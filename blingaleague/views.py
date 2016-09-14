from django.views.generic import TemplateView


class Home(TemplateView):
    template_name = 'blingaleague/home.html'


class Standings(TemplateView):
    template_name = 'blingaleague/standings.html'

