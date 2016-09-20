import decimal

from collections import defaultdict

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

    def __str__(self):
        return self.year


class MemberRecord(object):
    def __init__(self, member_id, years, include_playoffs=False):
        self.years = set(years)
        self.member = Member.objects.get(pk=member_id)
        self.include_playoffs = include_playoffs

    @cached_property
    def games(self):
        return self.wins + self.losses

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
        return decimal.Decimal(self.win_count) / decimal.Decimal(self.win_count + self.loss_count)

    @cached_property
    def points(self):
        return sum(map(lambda x: x.winner_score, self.wins)) + sum(map(lambda x: x.loser_score, self.losses))

    @cached_property
    def playoff_finish(self):
        if len(self.years) != 1:
            return ''

        season = Season.objects.get(year=self.years.pop())

        if self.member == season.place_1:
            return "Blingabowl %s champion" % season.blingabowl

        if self.member == season.place_2:
            return "Blingabowl %s runner-up" % season.blingabowl

        if self.member == season.place_3:
            return 'Third place'

        return ''

    def __str__(self):
        text = "%s (%s-%s)" % (self.member, self.win_count, self.loss_count)
        if self.playoff_finish:
            text = "%s - %s" % (text, self.playoff_finish)
        return text

    def __repr__(self):
        return str(self)


class Standings(object):
    def __init__(self, year=None, all_time=False, include_playoffs=False):
        self.year = year
        self.all_time = all_time
        self.include_playoffs = include_playoffs

        if self.all_time:
            self.year = None
            self.season = None
            self.headline = None
        else:
            if self.year is None:
                # if we didn't specify all_time, that means we need a current year
                self.year = Game.objects.all().order_by('-year').values_list('year', flat=True)[0]

            self.season = Season.objects.get(year=self.year)
            self.headline = "Blingabowl %s: %s def. %s" % (self.season.blingabowl, self.season.place_1, self.season.place_2)

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

        member_records = [MemberRecord(member_id, years, include_playoffs=self.include_playoffs) for member_id, years in member_years.items()]

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
