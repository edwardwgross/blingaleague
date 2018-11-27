import csv
import datetime
import decimal
import nvd3

from collections import defaultdict

from django.core.cache import caches
from django.db.models import F
from django.http import HttpResponse
from django.views.generic import TemplateView

from blingaleague.models import REGULAR_SEASON_WEEKS, \
                                Game, Week, Member, TeamSeason, Year, Matchup, \
                                OUTCOME_WIN, OUTCOME_LOSS

from .forms import CHOICE_BLANGUMS, CHOICE_SLAPPED_HEARTBEAT, \
                   CHOICE_WINS, CHOICE_LOSSES, \
                   CHOICE_REGULAR_SEASON, CHOICE_PLAYOFFS, \
                   CHOICE_MADE_PLAYOFFS, CHOICE_MISSED_PLAYOFFS, \
                   CHOICE_CLINCHED_BYE, CHOICE_CLINCHED_PLAYOFFS, \
                   CHOICE_ELIMINATED_EARLY, \
                   GameFinderForm, SeasonFinderForm
from .utils import sorted_seasons_by_attr, \
                   sorted_expected_wins_odds, \
                   build_belt_holder_list


CACHE = caches['blingaleague']

PREFIX_WINNER = 'winner'

PREFIX_LOSER = 'loser'

# number of games to qualify for top seasons
# leaderboard for non-counting stats
TOP_SEASONS_STAT_THRESHOLD = 6


class CSVResponseMixin(object):

    base_csv_filename = 'blingaleague_{}.csv'

    @property
    def filename(self):
        return self.base_csv_filename.format(
            datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
        )

    def generate_csv_data(self, result_list):
        raise NotImplementedError('Must be defined by the subclass')

    def render_to_csv(self, result_list):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = "attachment; filename={}".format(self.filename)

        csv_writer = csv.writer(response)
        for row in self.generate_csv_data(result_list):
            csv_writer.writerow(row)

        return response


class WeeklyScoresView(TemplateView):
    template_name = 'blingalytics/weekly_scores.html'

    def get(self, request):
        context = {
            'weeks': sorted(
                Week.regular_season_weeks(),
                key=lambda x: (x.year, x.week),
            ),
        }

        return self.render_to_response(context)


class ExpectedWinsView(TemplateView):
    template_name = 'blingalytics/expected_wins.html'

    def _expected_wins_graph(self, score):
        min_score = Game.objects.all().order_by('loser_score')[0].loser_score
        max_score = Game.objects.all().order_by('-winner_score')[0].winner_score

        interval = 5
        min_x = interval * (min_score // interval)
        max_x = interval * (max_score // interval) + interval  # add interval to round up

        # add interval because range() is exclusive at the high end
        x_data = list(range(int(min_x), int(max_x) + interval, interval))
        if score is not None:
            x_data = sorted(x_data + [score])

        x_data = list(map(float, x_data))
        y_data = list(map(float, map(Game.expected_wins, x_data)))

        graph = nvd3.lineChart(
            name='expected_wins',
            width=600,
            height=400,
            x_axis_format='.2f',
            y_axis_format='.3f',
            show_legend=False,
        )

        graph.add_serie(
            x=x_data,
            y=y_data,
            name='Expected Wins',
        )

        graph.buildcontent()
        graph.buildhtml()

        return graph

    def get(self, request):
        expected_wins = None

        score = request.GET.get('score', None)
        if score is not None:
            score = decimal.Decimal(score)
            expected_wins = Game.expected_wins(score)

        context = {
            'score': score,
            'expected_wins': expected_wins,
            'expected_wins_graph': self._expected_wins_graph(score),
        }

        return self.render_to_response(context)


class GameFinderView(CSVResponseMixin, TemplateView):
    template_name = 'blingalytics/game_finder.html'

    base_csv_filename = 'game_finder_{}.csv'

    def filter_games(self, form_data):
        base_games = Game.objects.all()

        if form_data['year_min'] is not None:
            base_games = base_games.filter(year__gte=form_data['year_min'])
        if form_data['year_max'] is not None:
            base_games = base_games.filter(year__lte=form_data['year_max'])

        if form_data['week_min'] is not None:
            base_games = base_games.filter(week__gte=form_data['week_min'])
        if form_data['week_max'] is not None:
            base_games = base_games.filter(week__lte=form_data['week_max'])

        if form_data['week_type'] == CHOICE_REGULAR_SEASON:
            base_games = base_games.filter(week__lte=REGULAR_SEASON_WEEKS)
        elif form_data['week_type'] == CHOICE_PLAYOFFS:
            base_games = base_games.filter(week__gt=REGULAR_SEASON_WEEKS)

        margin_min = form_data['margin_min']
        margin_max = form_data['margin_max']
        if margin_min is not None:
            base_games = base_games.filter(loser_score__lte=F('winner_score') - margin_min)
        if margin_max is not None:
            base_games = base_games.filter(loser_score__gte=F('winner_score') - margin_max)

        wins_only = form_data['outcome'] == CHOICE_WINS
        losses_only = form_data['outcome'] == CHOICE_LOSSES

        teams = form_data['teams']
        score_min = form_data['score_min']
        score_max = form_data['score_max']
        awards = form_data['awards']
        streak_min = form_data['streak_min']

        team_prefixes = (PREFIX_WINNER, PREFIX_LOSER)
        if wins_only:
            team_prefixes = (PREFIX_WINNER,)
        elif losses_only:
            team_prefixes = (PREFIX_LOSER,)

        all_games = []
        for team_prefix in team_prefixes:
            type_kwargs = {}

            if len(teams) > 0:
                type_kwargs["%s__id__in" % team_prefix] = teams

            if score_min is not None:
                type_kwargs["%s_score__gte" % team_prefix] = score_min
            if score_max is not None:
                type_kwargs["%s_score__lte" % team_prefix] = score_max

            opponent_prefix = PREFIX_LOSER if team_prefix == PREFIX_WINNER else PREFIX_WINNER

            for game in base_games.filter(**type_kwargs):
                if CHOICE_BLANGUMS in awards and not game.blangums:
                    continue

                if CHOICE_SLAPPED_HEARTBEAT in awards and not game.slapped_heartbeat:
                    continue

                if streak_min is not None:
                    if team_prefix == PREFIX_WINNER and game.winner_streak < streak_min:
                        continue
                    if team_prefix == PREFIX_LOSER and game.loser_streak < streak_min:
                        continue

                outcome = OUTCOME_WIN
                streak = game.winner_streak
                if team_prefix == PREFIX_LOSER:
                    outcome = OUTCOME_LOSS
                    streak = game.loser_streak

                game_dict = {
                    'id': game.id,
                    'year': game.year,
                    'week': game.week,
                    'team': getattr(game, team_prefix),
                    'score': getattr(game, "%s_score" % team_prefix),
                    'opponent': getattr(game, opponent_prefix),
                    'opponent_score': getattr(game, "%s_score" % opponent_prefix),
                    'margin': game.margin,
                    'outcome': outcome,
                    'streak': streak,
                }

                extra_description = ''
                if game.playoff_title:
                    extra_description = game.playoff_title
                elif team_prefix == PREFIX_WINNER and game.blangums:
                    extra_description = 'Team Blangums'
                elif team_prefix == PREFIX_LOSER and game.slapped_heartbeat:
                    extra_description = 'Slapped Heartbeat'

                game_dict['extra_description'] = extra_description

                all_games.append(game_dict)

        return sorted(all_games, key=lambda x: (x['year'], x['week'], -x['score']))

    def build_summary(self, games):
        games_counted = set()
        game_dict = defaultdict(lambda: defaultdict(int))

        for game in games:
            if game['id'] in games_counted:
                continue

            if game['outcome'] == OUTCOME_WIN:
                winner = game['team']
                loser = game['opponent']
            else:
                winner = game['opponent']
                loser = game['team']

            game_dict[winner]['wins'] += 1
            game_dict[loser]['losses'] += 1
            game_dict[winner]['total'] += 1
            game_dict[loser]['total'] += 1

            games_counted.add(game['id'])

        teams = []
        for team, stats in sorted(game_dict.items(), key=lambda x: x[0].nickname):
            stats['team'] = team
            teams.append(stats)

        return {
            'teams': teams,
            'total': len(games_counted),
        }

    def generate_csv_data(self, games):
        csv_data = [
            [
                'Year',
                'Week',
                'Team',
                'W/L',
                'Score',
                'OppScore',
                'Opponent',
                'Margin',
                'Streak',
                'Notes',
            ],
        ]

        for game in games:
            csv_data.append([
                game['year'],
                game['week'],
                game['team'].nickname,
                game['outcome'],
                game['score'],
                game['opponent_score'],
                game['opponent'].nickname,
                game['margin'],
                game['streak'],
                game['extra_description'],
            ])

        return csv_data

    def get(self, request):
        games = []

        game_finder_form = GameFinderForm(request.GET)
        if game_finder_form.is_valid():
            form_data = game_finder_form.cleaned_data

            games = self.filter_games(form_data)

        context = {
            'form': game_finder_form,
            'games': games,
            'summary': self.build_summary(games),
        }

        if 'csv' in request.GET:
            return self.render_to_csv(games)

        return self.render_to_response(context)


class SeasonFinderView(CSVResponseMixin, TemplateView):
    template_name = 'blingalytics/season_finder.html'

    base_csv_filename = 'season_finder_{}.csv'

    def filter_seasons(self, form_data):
        year_min = Year.min()
        year_max = Year.max()
        if form_data['year_min'] is not None:
            year_min = form_data['year_min']
        if form_data['year_max'] is not None:
            year_max = form_data['year_max']

        team_ids = form_data['teams']
        if len(team_ids) == 0:
            team_ids = Member.objects.all().order_by(
                'nickname', 'first_name', 'last_name',
            ).values_list('id', flat=True)

        for year in range(year_min, year_max + 1):
            for team_id in team_ids:
                ts = TeamSeason(team_id, year, week_max=form_data['week_max'])

                game_count = len(ts.games)
                if game_count == 0:
                    continue

                if form_data['week_max'] is not None:
                    # if the user specified the "Through X Weeks" field,
                    # and the value given is in the regular season,
                    # don't show seasons that haven't yet reached that week
                    # playoffs are special, though - teams with byes won't have the same logic
                    if form_data['week_max'] <= REGULAR_SEASON_WEEKS or not ts.bye:
                        if game_count < form_data['week_max']:
                            continue
                    elif ts.bye:
                        if game_count < (form_data['week_max'] - 1):
                            continue

                if form_data['wins_min'] is not None:
                    if ts.win_count < form_data['wins_min']:
                        continue
                if form_data['wins_max'] is not None:
                    if ts.win_count > form_data['wins_max']:
                        continue

                if form_data['expected_wins_min'] is not None:
                    if ts.expected_wins < form_data['expected_wins_min']:
                        continue
                if form_data['expected_wins_max'] is not None:
                    if ts.expected_wins > form_data['expected_wins_max']:
                        continue

                if form_data['points_min'] is not None:
                    if ts.points < form_data['points_min']:
                        continue
                if form_data['points_max'] is not None:
                    if ts.points > form_data['points_max']:
                        continue

                if form_data['place_min'] is not None:
                    if ts.place_numeric < form_data['place_min']:
                        continue
                if form_data['place_max'] is not None:
                    if ts.place_numeric > form_data['place_max']:
                        continue

                if form_data['playoffs'] == CHOICE_MADE_PLAYOFFS and not ts.made_playoffs:
                    continue
                elif form_data['playoffs'] == CHOICE_MISSED_PLAYOFFS and not ts.missed_playoffs:
                    continue

                clinched = form_data['clinched']
                if clinched == CHOICE_CLINCHED_BYE and not ts.clinched_bye:
                    continue
                elif clinched == CHOICE_CLINCHED_PLAYOFFS and not ts.clinched_playoffs:
                    continue
                elif clinched == CHOICE_ELIMINATED_EARLY and not ts.eliminated_early:
                    continue

                if form_data['bye'] and not ts.bye:
                    continue

                if form_data['champion'] and not ts.champion:
                    continue

                yield ts

    def build_summary_tables(self, seasons):
        team_dict = defaultdict(int)
        year_dict = defaultdict(int)

        for season in seasons:
            team_dict[season.team] += 1
            year_dict[season.year] += 1

        team_table = sorted(team_dict.items(), key=lambda x: x[0].nickname)
        year_table = sorted(year_dict.items())

        return {
            'teams': team_table,
            'years': year_table,
        }

    def generate_csv_data(self, seasons):
        csv_data = [
            [
                'Year',
                'Team',
                'Wins',
                'Losses',
                'W%',
                'Points',
                'Exp. W',
                'Exp. %',
                'Place',
                'Final Place',
                'Blangums',
                'Playoff Finish',
            ],
        ]

        for season in seasons:
            final_place = season.regular_season.place_numeric
            if season.regular_season.is_partial:
                final_place = None

            csv_data.append([
                season.year,
                season.team.nickname,
                season.win_count,
                season.loss_count,
                season.win_pct,
                season.points,
                season.expected_wins,
                season.expected_win_pct,
                season.place_numeric,
                final_place,
                season.blangums_count,
                season.playoff_finish,
            ])

        return csv_data

    def get(self, request):
        seasons = []

        season_finder_form = SeasonFinderForm(request.GET)
        if season_finder_form.is_valid():
            form_data = season_finder_form.cleaned_data

            seasons = list(self.filter_seasons(form_data))

        context = {
            'form': season_finder_form,
            'seasons': seasons,
            'summary_tables': self.build_summary_tables(seasons),
        }

        if 'csv' in request.GET:
            return self.render_to_csv(seasons)

        return self.render_to_response(context)


class TopSeasonsView(TemplateView):
    template_name = 'blingalytics/top_seasons.html'

    def generate_top_seasons_tables(self, row_limit):
        top_seasons_tables = []

        top_attrs_categories = (
            # title, attr, sort_desc, game_count_threshold
            ('Most Wins', 'win_count', True, 1),
            ('Fewest Wins', 'win_count', False, REGULAR_SEASON_WEEKS),
            ('Most Points', 'points', True, 1),
            ('Fewest Points', 'points', False, REGULAR_SEASON_WEEKS),
            ('Most Expected Wins', 'expected_wins', True, 1),
            ('Fewest Expected Wins', 'expected_wins', False, REGULAR_SEASON_WEEKS),
            ('Most Team Blangums', 'blangums_count', True, 1),
            ('Most Slapped Heartbeats', 'slapped_heartbeat_count', True, 1),
            ('Longest Winning Streak (single season)', 'longest_winning_streak', True, 1),
            ('Longest Losing Streak (single season)', 'longest_losing_streak', True, 1),
            ('Highest Average Score', 'average_score', True, TOP_SEASONS_STAT_THRESHOLD),
            ('Lowest Average Score', 'average_score', False, TOP_SEASONS_STAT_THRESHOLD),
            ('Highest Median Score', 'median_score', True, TOP_SEASONS_STAT_THRESHOLD),
            ('Lowest Median Score', 'median_score', False, TOP_SEASONS_STAT_THRESHOLD),
            ('Highest Minimum Score', 'min_score', True, TOP_SEASONS_STAT_THRESHOLD),
            ('Lowest Maximum Score', 'max_score', False, TOP_SEASONS_STAT_THRESHOLD),
            ('Highest Standard Deviation', 'stdev', True, TOP_SEASONS_STAT_THRESHOLD),
            ('Lowest Standard Deviation', 'stdev', False, TOP_SEASONS_STAT_THRESHOLD),
        )

        for title, attr, sort_desc, min_games in top_attrs_categories:
            table_rows = sorted_seasons_by_attr(
                attr,
                limit=row_limit,
                sort_desc=sort_desc,
                min_games=min_games,
            )
            top_seasons_tables.append({
                'title': title,
                'rows': table_rows,
            })

        win_odds_categories = (
            # title, win_count
            ('Highest Undefeated Odds', 13),
            ('Highest Winless Odds', 0),
        )

        for title, win_count in win_odds_categories:
            table_rows = sorted_expected_wins_odds(
                win_count,
                limit=row_limit,
                sort_desc=True,
            )
            top_seasons_tables.append({
                'title': title,
                'rows': table_rows,
            })

        return top_seasons_tables

    def get(self, request):
        row_limit = 10

        try:
            row_limit = int(request.GET.get('limit', row_limit))
        except ValueError:
            # ignore if user passed in a non-int
            pass

        cache_key = "blingalytics_top_seasons|{}".format(row_limit)

        if cache_key in CACHE:
            top_seasons_tables = CACHE.get(cache_key)
        else:
            top_seasons_tables = self.generate_top_seasons_tables(row_limit)
            CACHE.set(cache_key, top_seasons_tables)

        context = {
            'top_seasons_tables': top_seasons_tables,
        }

        return self.render_to_response(context)


class TeamVsTeamView(TemplateView):
    template_name = 'blingalytics/team_vs_team.html'

    def get(self, request):
        teams = Member.objects.all().order_by('defunct', 'first_name', 'last_name')

        grid = [{'team': team, 'matchups': Matchup.get_all_for_team(team.id)} for team in teams]

        context = {'grid': grid, 'teams': teams}

        return self.render_to_response(context)


class BeltHolderView(TemplateView):
    template_name = 'blingalytics/belt_holder.html'

    def get(self, request):
        belt_holder_list = build_belt_holder_list()

        belt_stats = defaultdict(lambda: defaultdict(int))
        for holder_data in belt_holder_list:
            holder = holder_data['holder']
            defense_count = holder_data['defense_count']

            belt_stats[holder]['occurrences'] += 1
            belt_stats[holder]['total_defense_count'] += defense_count

        belt_holder_summary = []
        for holder, stats in sorted(belt_stats.items(), key=lambda x: x[0].nickname):
            belt_holder_summary.append({
                'holder': holder,
                'occurrences': stats['occurrences'],
                'total_defense_count': stats['total_defense_count'],
            })

        context = {
            'belt_holder_list': belt_holder_list,
            'belt_holder_summary': belt_holder_summary,
        }

        return self.render_to_response(context)
