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


class MemberSeason(object):
    def __init__(self, year, member_id):
        self.year = year
        self.member = Member.objects.get(pk=member_id)

    @cached_property
    def games(self):
        return self.wins + self.losses

    @cached_property
    def wins(self):
        return list(self.member.games_won.filter(year=self.year, week__lte=REGULAR_SEASON_WEEKS))

    @cached_property
    def losses(self):
        return list(self.member.games_lost.filter(year=self.year, week__lte=REGULAR_SEASON_WEEKS))

    @cached_property
    def points(self):
        return sum(map(lambda x: x.winner_score, self.wins)) + sum(map(lambda x: x.loser_score, self.losses))

    def __str__(self):
        return "%s %s (%s-%s)" % (self.year, self.member, len(self.wins), len(self.losses))

    def __repr__(self):
        return str(self)


class Standings(object):
    def __init__(self, year=None, all_time=False, include_playoffs=False):
        self.year = year
        self.include_playoffs = include_playoffs

        if all_time:
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

        for game in self.games:
            results_by_member[game.winner]['wins'] += 1
            results_by_member[game.winner]['points'] += game.winner_score
            results_by_member[game.loser]['losses'] += 1
            results_by_member[game.loser]['points'] += game.loser_score

        if self.year is not None:
            results_by_member[self.season.place_1]['notes'] = "Blingabowl %s Champion" % self.season.blingabowl
            results_by_member[self.season.place_2]['notes'] = 'Runner-up'
            results_by_member[self.season.place_3]['notes'] = 'Third place'

        members_ordered = sorted(results_by_member.items(), key=lambda x: (x[1]['wins'], x[1]['points']), reverse=True)

        table = []
        for member, record in members_ordered:
            row = {'member': member}
            row.update(record)
            table.append(row)

        return table

    def __str__(self):
        if self.year:
            return "%s standings" % self.year
        else:
            return 'All-time standings'

    def __repr__(self):
        return str(self)
