from django.db.models import Avg, Sum

from django.views.generic import TemplateView

from blingaleague.models import REGULAR_SEASON_WEEKS, Game, Week


class WeeklyScoresView(TemplateView):
    template_name = 'blingalytics/weekly_scores.html'

    def get(self, request):
        weeks = []
        for year, week in Game.objects.filter(week__lte=REGULAR_SEASON_WEEKS).values_list('year', 'week').distinct():
            weeks.append(Week(year, week))

        context = {'weeks': sorted(weeks, key=lambda x: (x.year, x.week))}

        return self.render_to_response(context)


class ExpectedWinsView(TemplateView):
    template_name = 'blingaleague/home.html'

class GameFinderView(TemplateView):
    template_name = 'blingaleague/home.html'

