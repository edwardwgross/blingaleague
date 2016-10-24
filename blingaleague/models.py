import datetime
import decimal

from collections import defaultdict

from django.contrib.humanize.templatetags.humanize import ordinal
from django.core import urlresolvers
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db import models

from cached_property import cached_property

from .utils import int_to_roman


REGULAR_SEASON_WEEKS = 13
BLINGABOWL_WEEK = 16
FIRST_SEASON = 2008


class Member(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    nickname = models.CharField(max_length=50, blank=True, null=True)

    @cached_property
    def full_name(self):
        middle = ' '
        if self.nickname:
            middle = " \"%s\" " % self.nickname
        return "%s%s%s" % (self.first_name, middle, self.last_name)

    @cached_property
    def all_time_record(self):
        wins = self.games_won.filter(week__lte=REGULAR_SEASON_WEEKS).count()
        losses = self.games_lost.filter(week__lte=REGULAR_SEASON_WEEKS).count()
        return "%s-%s" % (wins, losses)

    @cached_property
    def all_time_record_with_playoffs(self):
        return "%s-%s" % (self.games_won.count(), self.games_lost.count())

    @cached_property
    def seasons(self):
        return TeamMultiSeasons(self.id)

    @cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.team', args=(self.id,))

    def __str__(self):
        return self.full_name

    def __repr__(self):
        return str(self)


class Game(models.Model):
    year = models.IntegerField(db_index=True)
    week = models.IntegerField(db_index=True)
    winner = models.ForeignKey(Member, db_index=True, related_name='games_won')
    loser = models.ForeignKey(Member, db_index=True, related_name='games_lost')
    winner_score = models.DecimalField(max_digits=6, decimal_places=2, db_index=True)
    loser_score = models.DecimalField(max_digits=6, decimal_places=2, db_index=True)
    notes = models.TextField(blank=True, null=True)

    @cached_property
    def week_object(self):
        return Week(self.year, self.week)

    @cached_property
    def blangums(self):
        return self.winner == self.week_object.blangums

    @cached_property
    def slapped_heartbeat(self):
        return self.loser == self.week_object.slapped_heartbeat

    @cached_property
    def title(self):
        if self.playoff_title:
            return self.playoff_title
        return str(self.week_object)

    @cached_property
    def playoff_title(self):
        if self.week > REGULAR_SEASON_WEEKS:
            try:
                season = Season.objects.get(year=self.year)
                if self.week == BLINGABOWL_WEEK:
                    if self.winner == season.place_1:
                        playoff_title = "Blingabowl %s" % season.blingabowl
                    else:
                        playoff_title = 'Third-place game'
                elif self.week == (BLINGABOWL_WEEK - 1):
                    if self.winner == season.place_5:
                        playoff_title = 'Fifth-place game'
                    else:
                        playoff_title = 'Semifinals'
                else:
                    playoff_title = 'Quarterfinals'

                return "%s, %s" % (playoff_title, self.year)
            except Season.DoesNotExist:
                pass  # current season won't have one

        return ''

    @cached_property
    def margin(self):
        return self.winner_score - self.loser_score

    @classmethod
    def expected_wins(cls, game_scores):
        all_scores = []
        for winner_score, loser_score in Game.objects.all().values_list('winner_score', 'loser_score'):
            all_scores.extend([winner_score, loser_score])

        all_scores_count = decimal.Decimal(len(all_scores))

        def _win_expectancy(score):
            win_count = len(filter(lambda x: x < score, all_scores))
            return decimal.Decimal(win_count) / all_scores_count

        return sum(_win_expectancy(score) for score in game_scores)

    def validate_unique(self, **kwargs):
        errors = {}

        other_weekly_games = Game.objects.filter(year=self.year, week=self.week)

        if (self.year < 2012 and other_weekly_games.count() >= 6) or other_weekly_games.count() >= 7:
            errors.setdefault(NON_FIELD_ERRORS, []).append(ValidationError(message='Too many games', code='too_many_games'))

        for game in other_weekly_games:
            if set([self.winner, self.loser]) & set([game.winner, game.loser]):
                errors.setdefault(NON_FIELD_ERRORS, []).append(ValidationError(message='Duplicate team', code='duplicate_team'))

        if self.winner_score < self.loser_score:
            errors.setdefault(NON_FIELD_ERRORS, []).append(ValidationError(message='Loser score greater than winner score', code='loser_gt_winner'))

        if self.week > 1 and self.week <= 13:
            previous_week_games = Game.objects.filter(year=self.year, week=self.week-1)
            if (self.year >= 2012 and previous_week_games.count() < 7) or previous_week_games.count() < 6:
                errors.setdefault(NON_FIELD_ERRORS, []).append(ValidationError(message='Previous week isn\'t done', code='previous_not_done'))

        if errors:
            raise ValidationError(errors)

        # don't neglect the default validation
        super(Game, self).validate_unique(**kwargs)

    def __str__(self):
        return "%s: %s def. %s" % (self.title, self.winner, self.loser)

    def __repr__(self):
        return str(self)


class Season(models.Model):
    year = models.IntegerField(primary_key=True)
    place_1 = models.ForeignKey(Member, db_index=True, null=True, default=None, related_name='first_place_finishes')
    place_2 = models.ForeignKey(Member, db_index=True, null=True, default=None, related_name='second_place_finishes')
    place_3 = models.ForeignKey(Member, db_index=True, null=True, default=None, related_name='third_place_finishes')
    place_4 = models.ForeignKey(Member, db_index=True, null=True, default=None, related_name='fourth_place_finishes')
    place_5 = models.ForeignKey(Member, db_index=True, null=True, default=None, related_name='fifth_place_finishes')
    place_6 = models.ForeignKey(Member, db_index=True, null=True, default=None, related_name='sixth_place_finishes')

    @cached_property
    def playoff_results(self):
        return (
            self.place_1,
            self.place_2,
            self.place_3,
            self.place_4,
            self.place_5,
            self.place_6,
        )

    @cached_property
    def blingabowl(self):
        return int_to_roman(self.year + 1 - FIRST_SEASON)

    @cached_property
    def robscores(self):
        robscores = defaultdict(lambda: 0)

        for place, team in enumerate(self.playoff_results):
            robscores[team] += 1 # all playoff teams get one

            # there are bonuses for finishing in the top three
            if team == self.place_1:
                robscores[team] += 1.0
            elif team == self.place_2:
                robscores[team] += 0.5
            elif team == self.place_3:
                robscores[team] += 0.25

        # regular-season winner and runner-up also get something
        standings = Standings(year=self.year)
        robscores[standings.table[0].team] += 0.5
        robscores[standings.table[1].team] += 0.25

        return robscores

    @cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.standings_year', args=(self.year,))

    def team_to_playoff_finish(self, team):
        for place, finish_team in enumerate(self.playoff_results):
            if team == finish_team:
                return place + 1
        return None

    def __str__(self):
        return str(self.year)

    def __repr__(self):
        return str(self)


class TeamSeason(object):

    def __init__(self, team_id, year, include_playoffs=False, week_max=None):
        self.year = int(year)
        self.team = Member.objects.get(id=team_id)
        if week_max is None:
            if include_playoffs:
                week_max = BLINGABOWL_WEEK
            else:
                week_max = REGULAR_SEASON_WEEKS
        self.week_max = week_max

        try:
            self.season = Season.objects.get(year=self.year)
        except Season.DoesNotExist:
            self.season = None  # this is ok, it's the current season

    @cached_property
    def games(self):
        return sorted(self.wins + self.losses, key=lambda x: (x.year, x.week))

    @cached_property
    def wins(self):
        wins = self.team.games_won.filter(year=self.year, week__lte=self.week_max)
        return list(wins)

    @cached_property
    def losses(self):
        losses = self.team.games_lost.filter(year=self.year, week__lte=self.week_max)
        return list(losses)

    @cached_property
    def win_count(self):
        return len(self.wins)

    @cached_property
    def loss_count(self):
        return len(self.losses)

    @cached_property
    def record(self):
        return "%s-%s" % (self.win_count, self.loss_count)

    @cached_property
    def win_pct(self):
        return decimal.Decimal(self.win_count) / decimal.Decimal(len(self.games))

    @cached_property
    def points(self):
        return sum(map(lambda x: x.winner_score, self.wins)) + sum(map(lambda x: x.loser_score, self.losses))

    @cached_property
    def standings(self):
        return Standings(year=self.year)

    @cached_property
    def place_numeric(self):
        return self.standings.team_to_place(self.team)

    @cached_property
    def place(self):
        if self.place_numeric is None:
            return '?'

        return ordinal(self.place_numeric)

    @cached_property
    def playoff_finish(self):
        if self.season is None:
            return ''

        if self.team == self.season.place_1:
            return "Blingabowl %s champion" % self.season.blingabowl

        playoff_finish = self.season.team_to_playoff_finish(self.team)
        if playoff_finish is not None:
            return ordinal(playoff_finish)

        return ''

    @cached_property
    def playoffs(self):
        if self.season is None:
            return False
        return self.season.team_to_playoff_finish(self.team) is not None

    @cached_property
    def bye(self):
        if self.season is None:
            return False
        return self.place_numeric <= 2

    @cached_property
    def champion(self):
        if self.season is None:
            return False
        return (self.team == self.season.place_1)

    @cached_property
    def expected_wins(self):
        game_scores = [w.winner_score for w in self.wins] + [l.loser_score for l in self.losses]
        return Game.expected_wins(game_scores)

    @cached_property
    def expected_win_pct(self):
        return decimal.Decimal(self.expected_wins) / decimal.Decimal(len(self.games))

    @cached_property
    def blangums_count(self):
        blangums = filter(lambda x: x.week_object.blangums == self.team and x.week <= REGULAR_SEASON_WEEKS, self.games)
        return len(blangums)

    @cached_property
    def robscore(self):
        if self.season is None:
            return 0

        robscore = 0

        if self.playoffs:
            robscore += 1

        if self.champion:
            robscore += 1
        elif self.team == self.season.place_2:
            robscore += 0.5
        elif self.team == self.season.place_3:
            robscore += 0.25

        if self.place_numeric == 1:
            robscore += 0.5
        elif self.place_numeric == 2:
            robscore += 0.25

        return robscore

    @cached_property
    def headline(self):
        regular_season = self.regular_season
        text = "%s-%s, %s points, %s" % (regular_season.win_count, regular_season.loss_count, regular_season.points, regular_season.place)
        if self.playoff_finish:
            text = "%s (regular season), %s (playoffs)" % (text, self.playoff_finish)
        return text

    @cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.team_season', args=(self.team.id, self.year))

    @cached_property
    def previous(self):
        prev_ts = TeamSeason(self.team.id, self.year - 1, week_max=self.week_max)

        if len(prev_ts.games) == 0:
            return None

        return prev_ts

    @cached_property
    def next(self):
        next_ts = TeamSeason(self.team.id, self.year + 1, week_max=self.week_max)

        if len(next_ts.games) == 0:
            return None

        return next_ts

    @cached_property
    def regular_season(self):
        return TeamSeason(self.team.id, self.year, week_max=REGULAR_SEASON_WEEKS)

    @cached_property
    def most_similar(self):
        limit = 10
        similar_seasons = []
        min_score = 900
        while len(similar_seasons) < limit:
            similar_seasons = list(self._filter_similar_seasons(min_score))
            min_score -= 100

        sorted_seasons = sorted(similar_seasons, key=lambda x: x['score'], reverse=True)[:limit]
        # we want to show the end result of the season
        return map(lambda x: {'season': x['season'].regular_season, 'score': x['score']}, sorted_seasons)

    def similarity_score(self, other_season):
        score = 1000
        score -= abs(self.win_count - other_season.win_count) * 100
        score -= int(abs(self.points - other_season.points) / 10)
        score -= int(abs(self.expected_wins - other_season.expected_wins) * 100)
        return score

    def _filter_similar_seasons(self, threshold):
        base_season = self
        week_max = self.win_count + self.loss_count

        if week_max > REGULAR_SEASON_WEEKS:
            base_season = self.regular_season
            week_max = REGULAR_SEASON_WEEKS

        for year in range(FIRST_SEASON, datetime.datetime.today().year + 1):
            for team_id in Member.objects.all().values_list('id', flat=True):
                if team_id == base_season.team.id and year == base_season.year:
                    continue

                team_season = TeamSeason(team_id, year, week_max=week_max)

                if len(team_season.games) == 0:
                    continue

                sim_score = base_season.similarity_score(team_season)
                if sim_score >= threshold:
                    yield {'season': team_season, 'score': sim_score}

    def __str__(self):
        return "%s, %s" % (self.team, self.year)

    def __repr__(self):
        return str(self)


class TeamMultiSeasons(TeamSeason):

    def __init__(self, team_id, years=None, include_playoffs=False):
        if years is None:
            years = Game.objects.all().values_list('year', flat=True).distinct()

        self.years = sorted(years)
        self.team = Member.objects.get(id=team_id)
        self.include_playoffs = include_playoffs

    @cached_property
    def team_seasons(self):
        team_seasons = []
        for year in self.years:
            team_season = TeamSeason(self.team.id, year, include_playoffs=self.include_playoffs)
            if len(team_season.games) > 0:
                team_seasons.append(team_season)
        return team_seasons

    @cached_property
    def wins(self):
        wins = []
        for team_season in self:
            wins += team_season.wins
        return wins

    @cached_property
    def losses(self):
        losses = []
        for team_season in self:
            losses += team_season.losses
        return losses

    @cached_property
    def robscore(self):
        return sum(team_season.robscore for team_season in self)

    @cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.team', args=(self.team.id,))

    def __iter__(self):
        for team_season in self.team_seasons:
            yield team_season

    def __str__(self):
        return "%s - %s" % (self.team, ', '.join(map(str, self.years)))

    def __repr__(self):
        return str(self)


class Standings(object):

    def __init__(self, year=None, all_time=False, include_playoffs=False):
        self.year = year
        self.all_time = all_time
        self.include_playoffs = include_playoffs

        self.season = None
        self.headline = None

        if self.all_time:
            self.year = None
        else:
            if self.year is None:
                # if we didn't specify all_time, that means we need a current year
                self.year = Week.latest().year

            try:
                self.season = Season.objects.get(year=self.year)
                if self.season.place_1:
                    self.headline = "Blingabowl %s: %s def. %s" % (self.season.blingabowl, self.season.place_1, self.season.place_2)
            except Season.DoesNotExist:
                pass  # won't exist for the current season

    @cached_property
    def table(self):
        team_records = []

        for member in Member.objects.all():
            if self.all_time:
                team_record = TeamMultiSeasons(member.id, include_playoffs=self.include_playoffs)
            else:
                team_record = TeamSeason(member.id, self.year, include_playoffs=self.include_playoffs)

            if len(team_record.games) > 0:
                team_records.append(team_record)

        return sorted(team_records, key=lambda x: (x.win_pct, x.points), reverse=True)

    @cached_property
    def href(self):
        if self.year is not None:
            return urlresolvers.reverse_lazy('blingaleague.standings_year', args=(self.year,))
        elif self.all_time:
            getargs = ''
            if self.include_playoffs:
                getargs = '?include_playoffs'
            return "%s%s" % (urlresolvers.reverse_lazy('blingaleague.standings_all_time'), getargs)

    def team_to_place(self, team):
        for place, team_record in enumerate(self.table):
            if team == team_record.team:
                return place + 1

        return None

    def __str__(self):
        if self.year:
            text = "%s standings" % self.year
        else:
            text = 'All-time standings'

        if self.include_playoffs:
            text = "%s (including playoffs)" % text

        return text

    def __repr__(self):
        return str(self)


class Week(object):

    def __init__(self, year, week):
        self.year = int(year)
        self.week = int(week)

    @cached_property
    def games(self):
        games = Game.objects.filter(year=self.year, week=self.week)
        return games.order_by('notes', '-winner_score', '-loser_score')

    @cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.week', args=(self.year, self.week))

    @cached_property
    def average_score(self):
        return sum(map(lambda x: x.winner_score + x.loser_score, self.games)) / (2 * self.games.count())

    @cached_property
    def average_margin(self):
        return sum(map(lambda x: x.margin, self.games)) / self.games.count()

    @cached_property
    def previous(self):
        if self.week == 1:
            prev_week = Week(self.year - 1, BLINGABOWL_WEEK)
        else:
            prev_week = Week(self.year, self.week - 1)

        if prev_week.games.count() == 0:
            return None

        return prev_week

    @cached_property
    def next(self):
        if self.week == BLINGABOWL_WEEK:
            next_week = Week(self.year + 1, 1)
        else:
            next_week = Week(self.year, self.week + 1)

        if next_week.games.count() == 0:
            return None

        return next_week

    @cached_property
    def blangums(self):
        return self.games.order_by('-winner_score')[0].winner

    @cached_property
    def slapped_heartbeat(self):
        return self.games.order_by('loser_score')[0].loser

    @cached_property
    def headline(self):
        return "Team Blangums: %s (%s) / Slapped Heartbeat: %s (%s)" % (self.blangums.winner, self.blangums.winner_score, self.slapped_heartbeat.loser, self.slapped_heartbeat.loser_score)

    @classmethod
    def latest(cls):
        year, week = Game.objects.all().order_by('-year', '-week').values_list('year', 'week')[0]
        return cls(year, week)

    def __str__(self):
        return "Week %s, %s" % (self.week, self.year)

    def __repr__(self):
        return str(self)


class Matchup(object):

    def __init__(self, team1_id, team2_id):
        self.team1 = Member.objects.get(id=team1_id)
        self.team2 = Member.objects.get(id=team2_id)

    @cached_property
    def games(self):
        games = self.team1_wins + self.team2_wins
        return sorted(games, key=lambda x: (x.year, x.week), reverse=True)

    @cached_property
    def team1_wins(self):
        return list(Game.objects.filter(winner=self.team1, loser=self.team2))

    @cached_property
    def team2_wins(self):
        return list(Game.objects.filter(winner=self.team2, loser=self.team1))

    @cached_property
    def team1_count(self):
        return len(self.team1_wins)

    @cached_property
    def team2_count(self):
        return len(self.team2_wins)

    @cached_property
    def record(self):
        return "%s-%s" % (self.team1_count, self.team2_count)

    @cached_property
    def headline(self):
        if self.team1_count == self.team2_count:
            return "All-time series tied, %s-%s" % (self.team1_count, self.team2_count)
        else:
            text = "%s leads all-time series, %s-%s"
            if self.team1_count > self.team2_count:
                return text % (self.team1, self.team1_count, self.team2_count)
            else:
                return text % (self.team2, self.team2_count, self.team1_count)

    @cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.matchup', args=(self.team1.id, self.team2.id))

    @classmethod
    def get_all_for_team(cls, team1_id):
        return [cls(team1_id, team2_id) for team2_id in Member.objects.all().order_by('first_name', 'last_name').values_list('id', flat=True)]

    def __str__(self):
        return "%s vs. %s" % (self.team1, self.team2)

    def __repr__(self):
        return str(self)

