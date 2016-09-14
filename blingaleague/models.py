from django.db import models


class Member(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    nickname = models.CharField(max_length=50, blank=True, null=True)

    @property
    def full_name(self):
        middle = ' '
        if self.nickname:
            middle = " \"%s\" " % self.nickname
        return "%s%s%s" % (self.first_name, middle, self.last_name)


class Game(models.Model):
    year = models.IntegerField()
    week = models.IntegerField()
    winner = ForeignKey(Member)
    loser = ForeignKey(Member)
    winner_score = DecimalField(decimal_places=2)
    loser_score = DecimalField(decimal_places=2)
    notes = models.TextField(blank=True, null=True)

