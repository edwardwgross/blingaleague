from collections import defaultdict

from django.db import models

from cached_property import cached_property


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
        return list(self.member.games_won.filter(year=self.year, week__lte=13))

    @cached_property
    def losses(self):
        return list(self.member.games_lost.filter(year=self.year, week__lte=13))

    @cached_property
    def points(self):
        return sum(map(lambda x: x.winner_score, self.wins)) + sum(map(lambda x: x.loser_score, self.losses))

    def __str__(self):
        return "%s %s (%s-%s)" % (self.year, self.member, len(self.wins), len(self.losses))

    def __repr__(self):
        return str(self)


class Standings(object):
    def __init__(self, year):
        self.year = year

    @cached_property
    def games(self):
        return Game.objects.filter(year=self.year, week__lte=13)

    @cached_property
    def table(self):
        results_by_member = defaultdict(lambda: defaultdict(lambda: 0))

        for game in self.games:
            results_by_member[game.winner]['wins'] += 1
            results_by_member[game.winner]['points'] += game.winner_score
            results_by_member[game.loser]['losses'] += 1
            results_by_member[game.loser]['points'] += game.loser_score

        members_ordered = sorted(results_by_member.items(), key=lambda x: (x[1]['wins'], x[1]['points']), reverse=True)

        table = []
        for member, record in members_ordered:
            row = {'member': member}
            row.update(record)
            table.append(row)

        return table

    def __str__(self):
        return "%s: %s" % (self.year, ' def. '.join(map(lambda x: str(x['member']), self.table[:2])))

    def __repr__(self):
        return str(self)
