import decimal

from collections import defaultdict

from django.core import urlresolvers
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db import models

from cached_property import cached_property

from .utils import int_to_roman


REGULAR_SEASON_WEEKS = 13
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

    @classmethod
    def expected_wins(cls, game_scores):
        all_scores = []
        for winner_score, loser_score in Game.objects.all().values_list('winner_score', 'loser_score'):
            all_scores.extend([winner_score, loser_score])

        def _win_expectancy(score):
            win_count = len(filter(lambda x: x < score, all_scores))
            return decimal.Decimal(win_count) / decimal.Decimal(len(all_scores))

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
        return "%s, week %s: %s def. %s" % (self.year, self.week, self.winner, self.loser)

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

        for place, member in enumerate(self.playoff_results):
            robscores[member] += 1 # all playoff teams get one

            # there are bonuses for finishing in the top three
            if member == self.place_1:
                robscores[member] += 1.0
            elif member == self.place_2:
                robscores[member] += 0.5
            elif member == self.place_3:
                robscores[member] += 0.25

        # regular-season winner and runner-up also get something
        standings = Standings(year=self.year)
        robscores[standings.table[0].member] += 0.5
        robscores[standings.table[1].member] += 0.25

        return robscores

    @cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.standings_year', args=(self.year,))

    def __str__(self):
        return str(self.year)


class TeamRecord(object):

    def __init__(self, member_id, years, include_playoffs=False):
        self.years = set(years)
        self.member = Member.objects.get(pk=member_id)
        self.include_playoffs = include_playoffs

        self.season = None
        if len(self.years) == 1:
            try:
                self.season = Season.objects.get(year=list(self.years)[0])
            except Season.DoesNotExist:
                pass # this is ok, it's the current season

    @cached_property
    def games(self):
        return sorted(self.wins + self.losses, key=lambda x: (x.year, x.week))

    @cached_property
    def wins(self):
        wins = self.member.games_won.filter(year__in=self.years)
        if not self.include_playoffs:
            wins = wins.filter(week__lte=REGULAR_SEASON_WEEKS)
        return list(wins)

    @cached_property
    def losses(self):
        losses = self.member.games_lost.filter(year__in=self.years)
        if not self.include_playoffs:
            losses = losses.filter(week__lte=REGULAR_SEASON_WEEKS)
        return list(losses)

    @cached_property
    def win_count(self):
        return len(self.wins)

    @cached_property
    def loss_count(self):
        return len(self.losses)

    @cached_property
    def win_pct(self):
        return decimal.Decimal(self.win_count) / decimal.Decimal(len(self.games))

    @cached_property
    def points(self):
        return sum(map(lambda x: x.winner_score, self.wins)) + sum(map(lambda x: x.loser_score, self.losses))

    @cached_property
    def playoff_finish(self):
        if len(self.years) != 1 or self.season is None:
            return ''

        if self.member == self.season.place_1:
            return "Blingabowl %s champion" % self.season.blingabowl

        if self.member == self.season.place_2:
            return "Blingabowl %s runner-up" % self.season.blingabowl

        if self.member == self.season.place_3:
            return 'Third place'

        return ''

    @cached_property
    def expected_wins(self):
        game_scores = [w.winner_score for w in self.wins] + [l.loser_score for l in self.losses]
        return Game.expected_wins(game_scores)

    @cached_property
    def expected_win_pct(self):
        return decimal.Decimal(self.expected_wins) / decimal.Decimal(len(self.games))

    @cached_property
    def robscore(self):
        robscore = 0

        if len(self.years) > 1:
            return sum([TeamRecord(self.member.id, [year]).robscore for year in self.years])

        return self.season.robscores[self.member]

    @cached_property
    def headline(self):
        text = "%s-%s, %s points" % (self.win_count, self.loss_count, self.points)
        if self.playoff_finish:
            text = "%s - %s" % (text, self.playoff_finish)
        return text

    @cached_property
    def href(self):
        if len(self.years) == 1:
            url_name = 'blingaleague.team_season'
            args = (self.member.id, list(self.years)[0])
        else:
            url_name = 'blingaleague.team'
            args = (self.member.id,)
        return urlresolvers.reverse_lazy(url_name, args=args)

    def __str__(self):
        return "%s - %s" % (self.member, ', '.join(map(str, self.years)))

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
    def games(self):
        games = Game.objects.all()

        if self.year is not None:
            games = games.filter(year=self.year)

        if not self.include_playoffs:
            games = games.filter(week__lte=REGULAR_SEASON_WEEKS)

        return games

    @cached_property
    def table(self):
        results_by_member = defaultdict(lambda: defaultdict(lambda: 0))
        member_years = defaultdict(set)
        for game in self.games:
            member_years[game.winner.id].add(game.year)
            member_years[game.loser.id].add(game.year)

        member_records = [TeamRecord(member_id, years, include_playoffs=self.include_playoffs) for member_id, years in member_years.items()]

        return sorted(member_records, key=lambda x: (x.win_pct, x.points), reverse=True)

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
        self.year = year
        self.week = week

    @cached_property
    def games(self):
        games = Game.objects.filter(year=self.year, week=self.week)
        return games.order_by('-winner_score', '-loser_score')

    @cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.week', args=(self.year, self.week))

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

