import datetime
import decimal
import itertools
from collections import defaultdict
from statistics import mean

from django.contrib.humanize.templatetags.humanize import ordinal
from django.core import urlresolvers
from django.core.cache import caches
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db import models

from .utils import int_to_roman, fully_cached_property, clear_cached_properties


REGULAR_SEASON_WEEKS = 13
BLINGABOWL_WEEK = 16
BYE_TEAMS = 2
PLAYOFF_TEAMS = 6
FIRST_SEASON = 2008

BLINGABOWL_TITLE_BASE = 'Blingabowl'
SEMIFINALS_TITLE_BASE = 'Semifinals'
QUARTERFINALS_TITLE_BASE = 'Quarterfinals'
THIRD_PLACE_TITLE_BASE = 'Third-place game'
FIFTH_PLACE_TITLE_BASE = 'Fifth-place game'

SEASON_START_MONTH = 9


class Member(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    nickname = models.CharField(max_length=50, blank=True, null=True)
    defunct = models.BooleanField(default=False)
    email = models.EmailField(blank=True, null=True)

    @property
    def cache_key(self):
        return str(self.pk)

    @fully_cached_property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    @fully_cached_property
    def all_time_record(self):
        wins = self.games_won.filter(week__lte=REGULAR_SEASON_WEEKS).count()
        losses = self.games_lost.filter(week__lte=REGULAR_SEASON_WEEKS).count()
        return "{}-{}".format(wins, losses)

    @fully_cached_property
    def all_time_record_with_playoffs(self):
        return "{}-{}".format(self.games_won.count(), self.games_lost.count())

    @fully_cached_property
    def seasons(self):
        return TeamMultiSeasons(self.id)

    @fully_cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.team', args=(self.id,))

    def save(self, **kwargs):
        super().save(**kwargs)
        clear_cached_properties()

    def __str__(self):
        return self.full_name

    def __repr__(self):
        return str(self)

    class Meta:
        ordering = ['first_name', 'last_name']


class FakeMember(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    active = models.BooleanField(default=True)
    associated_member = models.ForeignKey(
        Member,
        db_index=True,
        blank=True,
        null=True,
        default=None,
        related_name='co_managers',
    )

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    class Meta:
        ordering = ['name']


class Game(models.Model):
    year = models.IntegerField(db_index=True)
    week = models.IntegerField(db_index=True)
    winner = models.ForeignKey(Member, db_index=True, related_name='games_won')
    loser = models.ForeignKey(Member, db_index=True, related_name='games_lost')
    winner_score = models.DecimalField(max_digits=6, decimal_places=2, db_index=True)
    loser_score = models.DecimalField(max_digits=6, decimal_places=2, db_index=True)
    notes = models.TextField(blank=True, null=True)

    @property
    def cache_key(self):
        return str(self.pk)

    @fully_cached_property
    def week_object(self):
        return Week(self.year, self.week)

    @fully_cached_property
    def blangums(self):
        return self.winner == self.week_object.blangums

    @fully_cached_property
    def slapped_heartbeat(self):
        return self.loser == self.week_object.slapped_heartbeat

    @fully_cached_property
    def title(self):
        if self.playoff_title:
            return self.playoff_title
        return str(self.week_object)

    @fully_cached_property
    def is_playoffs(self):
        return self.week > REGULAR_SEASON_WEEKS

    @fully_cached_property
    def playoff_title(self):
        if self.is_playoffs:
            try:
                season = Season.objects.get(year=self.year)
                if self.week == BLINGABOWL_WEEK:
                    if self.winner == season.place_1:
                        playoff_title = "{} {}".format(BLINGABOWL_TITLE_BASE, season.blingabowl)
                    else:
                        playoff_title = THIRD_PLACE_TITLE_BASE
                elif self.week == (BLINGABOWL_WEEK - 1):
                    if self.winner == season.place_5:
                        playoff_title = FIFTH_PLACE_TITLE_BASE
                    else:
                        playoff_title = SEMIFINALS_TITLE_BASE
                else:
                    playoff_title = QUARTERFINALS_TITLE_BASE

                return "{}, {}".format(playoff_title, self.year)
            except Season.DoesNotExist:
                pass  # current season won't have one

        return ''

    @fully_cached_property
    def margin(self):
        return self.winner_score - self.loser_score

    @fully_cached_property
    def total_score(self):
        return self.winner_score + self.loser_score

    @classmethod
    def expected_wins(cls, *game_scores, scaling_factor=1):
        all_scores = []
        game_results = Game.objects.all().values_list('winner_score', 'loser_score')
        for winner_score, loser_score in game_results:
            all_scores.extend([winner_score, loser_score])

        all_scores_count = decimal.Decimal(len(all_scores))

        def _win_expectancy(score):
            if all_scores_count == 0:
                return 0
            win_list = list(filter(lambda x: x < score, all_scores))
            win_count = len(win_list)
            raw_win_expectancy = decimal.Decimal(win_count) / all_scores_count
            scaled_win_expectancy = scaling_factor * raw_win_expectancy
            return min(1, scaled_win_expectancy)

        return sum(_win_expectancy(score) for score in game_scores)

    def other_weekly_games(self):
        return Game.objects.exclude(pk=self.pk).filter(year=self.year, week=self.week)

    def week_is_full(self):
        other_games_count = self.other_weekly_games().count()

        if (self.year < 2012 and other_games_count >= 6) or other_games_count >= 7:
            return True

        return False

    def clean(self):
        errors = {}

        if self.week_is_full():
            errors.setdefault(NON_FIELD_ERRORS, []).append(
                ValidationError(
                    message='Too many games',
                    code='too_many_games',
                ),
            )

        for game in self.other_weekly_games():
            if set([self.winner, self.loser]) & set([game.winner, game.loser]):
                errors.setdefault(NON_FIELD_ERRORS, []).append(
                    ValidationError(
                        message='Duplicate team',
                        code='duplicate_team',
                    ),
                )

        if self.winner_score < self.loser_score:
            errors.setdefault(NON_FIELD_ERRORS, []).append(
                ValidationError(
                    message='Loser score greater than winner score',
                    code='loser_gt_winner',
                ),
            )

        if self.week > 1 and self.week <= 13:
            target_game_count = 7
            if self.year < 2012:
                target_game_count = 6

            previous_week_games = Game.objects.filter(year=self.year, week=self.week-1)
            if previous_week_games.count() < target_game_count:
                errors.setdefault(NON_FIELD_ERRORS, []).append(
                    ValidationError(
                        message='Previous week isn\'t done',
                        code='previous_not_done',
                    ),
                )

        if errors:
            raise ValidationError(errors)

        super().clean()

    def save(self, **kwargs):
        super().save(**kwargs)
        clear_cached_properties()

    def __str__(self):
        return "{}: {} def. {}".format(self.title, self.winner, self.loser)

    def __repr__(self):
        return str(self)

    class Meta:
        # important note! do not add any ordering attribute to this Meta class,
        # as that causes .distinct() to not actually return distinct values
        # see https://stackoverflow.com/questions/2466496/select-distinct-values-from-a-table-field
        pass


def _place_field(related_name):
    return models.ForeignKey(
        Member,
        db_index=True,
        blank=True,
        null=True,
        default=None,
        related_name=related_name,
    )


class Season(models.Model):
    year = models.IntegerField(primary_key=True)
    place_1 = _place_field('first_place_finishes')
    place_2 = _place_field('second_place_finishes')
    place_3 = _place_field('third_place_finishes')
    place_4 = _place_field('fourth_place_finishes')
    place_5 = _place_field('fifth_place_finishes')
    place_6 = _place_field('sixth_place_finishes')

    @property
    def cache_key(self):
        return str(self.pk)

    @fully_cached_property
    def playoff_results(self):
        return (
            self.place_1,
            self.place_2,
            self.place_3,
            self.place_4,
            self.place_5,
            self.place_6,
        )

    @fully_cached_property
    def blingabowl(self):
        return int_to_roman(self.year + 1 - FIRST_SEASON)

    @fully_cached_property
    def robscores(self):
        robscores = defaultdict(lambda: 0)

        for place, team in enumerate(self.playoff_results):
            robscores[team] += 1  # all playoff teams get one

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

        return dict(robscores)

    @fully_cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.standings_year', args=(self.year,))

    def team_to_playoff_finish(self, team):
        for place, finish_team in enumerate(self.playoff_results):
            if team == finish_team:
                return place + 1
        return None

    def save(self, **kwargs):
        super().save(**kwargs)
        clear_cached_properties()

    def __str__(self):
        return str(self.year)

    def __repr__(self):
        return str(self)

    class Meta:
        ordering = ['-year']


class Year(object):

    def __init__(self, year, week_max=REGULAR_SEASON_WEEKS):
        self.year = int(year)
        self.week_max = min(int(week_max), REGULAR_SEASON_WEEKS)
        self.cache_key = '|'.join(map(str, (self.year, self.week_max)))

    @fully_cached_property
    def all_games(self):
        return Game.objects.filter(year=self.year, week__lte=self.week_max)

    @fully_cached_property
    def total_wins(self):
        return self.all_games.count()

    @fully_cached_property
    def total_raw_expected_wins(self):
        all_scores = []
        for winner_score, loser_score in self.all_games.values_list('winner_score', 'loser_score'):
            all_scores.extend([winner_score, loser_score])

        return Game.expected_wins(*all_scores)

    @fully_cached_property
    def expected_wins_scaling_factor(self):
        raw_scaling_factor = 1
        if self.total_raw_expected_wins > 0:
            raw_scaling_factor = (
                decimal.Decimal(self.total_wins) / decimal.Decimal(self.total_raw_expected_wins)
            )

        scaling_factor_weight = self.week_max * raw_scaling_factor
        regression_weight = REGULAR_SEASON_WEEKS - self.week_max

        return (scaling_factor_weight + regression_weight) / REGULAR_SEASON_WEEKS

    @classmethod
    def all(cls):
        all_years = set(Game.objects.all().values_list('year', flat=True))

        today = datetime.datetime.today()
        if today.month >= SEASON_START_MONTH:
            all_years.add(today.year)

        return all_years

    @classmethod
    def min(cls):
        return min(cls.all())

    @classmethod
    def max(cls):
        return max(cls.all())

    def __str__(self):
        return str(self.year)

    def __repr__(self):
        return str(self)


class TeamSeason(object):
    is_single_season = True

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

        self.year_object = Year(self.year, week_max=self.week_max)

        self.cache_key = '|'.join(map(str, (team_id, year, include_playoffs, week_max)))

    @fully_cached_property
    def games(self):
        return sorted(self.wins + self.losses, key=lambda x: (x.year, x.week))

    @fully_cached_property
    def wins(self):
        wins = self.team.games_won.filter(year=self.year, week__lte=self.week_max)
        return list(wins)

    @fully_cached_property
    def losses(self):
        losses = self.team.games_lost.filter(year=self.year, week__lte=self.week_max)
        return list(losses)

    @fully_cached_property
    def win_count(self):
        return len(self.wins)

    @fully_cached_property
    def loss_count(self):
        return len(self.losses)

    @fully_cached_property
    def record(self):
        return "{}-{}".format(self.win_count, self.loss_count)

    @fully_cached_property
    def win_pct(self):
        if len(self.games) == 0:
            return 0
        return decimal.Decimal(self.win_count) / decimal.Decimal(len(self.games))

    @fully_cached_property
    def points(self):
        return sum(self.game_scores)

    @fully_cached_property
    def standings(self):
        return Standings(year=self.year, week_max=self.week_max)

    @fully_cached_property
    def place_numeric(self):
        if self.week_max > REGULAR_SEASON_WEEKS:
            return self.regular_season.place_numeric
        return self.standings.team_to_place(self.team)

    @fully_cached_property
    def place(self):
        if self.place_numeric is None:
            return '?'
        return ordinal(self.place_numeric)

    @fully_cached_property
    def playoff_finish(self):
        if not self.is_single_season:
            return ''

        if self.season is None:
            return ''

        if self.team == self.season.place_1:
            return "Blingabowl {} champion".format(self.season.blingabowl)

        playoff_finish = self.season.team_to_playoff_finish(self.team)
        if playoff_finish is not None:
            return ordinal(playoff_finish)

        return ''

    @fully_cached_property
    def playoffs(self):
        regular_season_games = self.regular_season.games
        regular_season_place = self.regular_season.place_numeric
        return (len(regular_season_games) == REGULAR_SEASON_WEEKS and
                regular_season_place <= PLAYOFF_TEAMS)

    @fully_cached_property
    def bye(self):
        regular_season_games = self.regular_season.games
        regular_season_place = self.regular_season.place_numeric
        return (len(regular_season_games) == REGULAR_SEASON_WEEKS and
                regular_season_place <= BYE_TEAMS)

    @fully_cached_property
    def champion(self):
        if self.season is None:
            return False
        return (self.team == self.season.place_1)

    @fully_cached_property
    def game_scores(self):
        return [w.winner_score for w in self.wins] + [l.loser_score for l in self.losses]

    @fully_cached_property
    def is_partial(self):
        return len(self.regular_season.games) < REGULAR_SEASON_WEEKS

    def expected_wins_function(self, *game_scores):
        return Game.expected_wins(
            *game_scores,
            scaling_factor=self.year_object.expected_wins_scaling_factor,
        )

    @fully_cached_property
    def expected_wins(self):
        return self.expected_wins_function(*self.game_scores)

    @fully_cached_property
    def expected_win_pct(self):
        if len(self.games) == 0:
            return 0
        return decimal.Decimal(self.expected_wins) / decimal.Decimal(len(self.games))

    @fully_cached_property
    def expected_win_distribution(self):
        if not self.is_single_season:
            # too expensive to calculate for more than one season
            return None

        expected_wins_by_game = list(
            map(
                self.expected_wins_function,
                self.regular_season.game_scores
            ),
        )

        num_games = len(expected_wins_by_game)

        outcome_combos = itertools.product([0, 1], repeat=num_games)

        win_distribution = defaultdict(decimal.Decimal)

        for outcome_combo in outcome_combos:
            win_count = 0
            running_prob = decimal.Decimal(1)
            for i in range(num_games):
                wp = expected_wins_by_game[i]
                outcome = outcome_combo[i]
                if outcome:
                    win_count += 1
                    running_prob *= wp
                else:
                    running_prob *= (1 - wp)

            win_distribution[win_count] += running_prob

        return dict(win_distribution)

    @fully_cached_property
    def blangums_count(self):
        def _is_blangums(game):
            return (game.week_object.blangums == self.team and
                    game.week <= REGULAR_SEASON_WEEKS)

        blangums_list = list(filter(_is_blangums, self.games))
        return len(blangums_list)

    @fully_cached_property
    def slapped_heartbeat_count(self):
        def _is_slapped_heartbeat(game):
            return (game.week_object.slapped_heartbeat == self.team and
                    game.week <= REGULAR_SEASON_WEEKS)

        slapped_heartbeat_list = list(filter(_is_slapped_heartbeat, self.games))
        return len(slapped_heartbeat_list)

    @fully_cached_property
    def robscore(self):
        if self.season is None:
            return 0

        return self.season.robscores.get(self.team, 0)

    @fully_cached_property
    def headline(self):
        regular_season = self.regular_season
        text = "{}-{}, {} points, {}".format(
            regular_season.win_count,
            regular_season.loss_count,
            regular_season.points,
            regular_season.place,
        )

        if self.playoff_finish:
            text = "{} (regular season), {} (playoffs)".format(text, self.playoff_finish)

        return text

    @fully_cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.team_season', args=(self.team.id, self.year))

    @fully_cached_property
    def previous(self):
        prev_ts = TeamSeason(self.team.id, self.year - 1, week_max=self.week_max)

        if len(prev_ts.games) == 0:
            return None

        return prev_ts

    @fully_cached_property
    def next(self):
        next_ts = TeamSeason(self.team.id, self.year + 1, week_max=self.week_max)

        if len(next_ts.games) == 0:
            return None

        return next_ts

    @fully_cached_property
    def level_up_links(self):
        return [
            {
                'description': 'Franchise index',
                'href': self.team.href,
            },
            {
                'description': str(self.standings),
                'href': self.standings.href,
            },
        ]

    @fully_cached_property
    def regular_season(self):
        return TeamSeason(self.team.id, self.year, week_max=REGULAR_SEASON_WEEKS)

    @fully_cached_property
    def win_loss_sequence(self):
        return map(lambda x: 'W' if self.team == x.winner else 'L', self.games)

    @fully_cached_property
    def most_similar(self):
        limit = 10
        similar_seasons = []
        min_score = 900
        while len(similar_seasons) < limit:
            similar_seasons = list(self._filter_similar_seasons(min_score))
            min_score -= 100

        def _ss_display(ss):
            # we want to show the end result of the season
            return {
                'season': ss['season'].regular_season,
                'score': ss['score'],
            }

        sorted_seasons = sorted(similar_seasons, key=lambda x: x['score'], reverse=True)[:limit]
        return map(_ss_display, sorted_seasons)

    def similarity_score(self, other_season):
        score = 1000
        score -= abs(self.win_count - other_season.win_count) * 100
        score -= len(len(self.win_loss_differences(other_season))) * 10
        score -= int(abs(self.points - other_season.points))
        score -= int(abs(self.expected_wins - other_season.expected_wins) * 100)
        return max(score, 0)

    def win_loss_differences(self, other_season):
        def _ne(seq):
            return seq[0] != seq[1]

        return filter(_ne, zip(self.win_loss_sequence, other_season.win_loss_sequence))

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

    @classmethod
    def all(cls):
        for year in Year.all():
            for team_id in Member.objects.all().values_list('id', flat=True):
                team_season = cls(team_id, year)
                if len(team_season.game_scores) > 0:
                    yield team_season

    def __str__(self):
        return "{}, {}".format(self.team, self.year)

    def __repr__(self):
        return str(self)


class TeamMultiSeasons(TeamSeason):
    is_single_season = False

    def __init__(self, team_id, years=None, include_playoffs=False, week_max=None):
        if years is None:
            years = Year.all()

        self.years = sorted(years)
        self.team = Member.objects.get(id=team_id)
        self.include_playoffs = include_playoffs
        self.week_max = week_max

        years_string = ','.join(map(str, self.years))
        self.cache_key = '|'.join(map(str, (team_id, years_string, include_playoffs, week_max)))

    @fully_cached_property
    def team_seasons(self):
        team_seasons = []
        for year in self.years:
            team_season = TeamSeason(
                self.team.id,
                year,
                include_playoffs=self.include_playoffs,
                week_max=self.week_max,
            )

            if len(team_season.games) > 0:
                team_seasons.append(team_season)

        return team_seasons

    @fully_cached_property
    def wins(self):
        wins = []
        for team_season in self:
            wins.extend(team_season.wins)
        return wins

    @fully_cached_property
    def losses(self):
        losses = []
        for team_season in self:
            losses.extend(team_season.losses)
        return losses

    @fully_cached_property
    def expected_wins(self):
        return sum(team_season.expected_wins for team_season in self)

    @fully_cached_property
    def robscore(self):
        return sum(team_season.robscore for team_season in self)

    @fully_cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.team', args=(self.team.id,))

    def __iter__(self):
        for team_season in self.team_seasons:
            yield team_season

    def __str__(self):
        return "{} - {}".format(self.team, ', '.join(map(str, self.years)))

    def __repr__(self):
        return str(self)


class Standings(object):

    def __init__(self, year=None, all_time=False, include_playoffs=False, week_max=None):
        self.year = year
        self.all_time = all_time
        self.include_playoffs = include_playoffs
        self.week_max = week_max

        self.season = None
        self.headline = None

        if self.all_time:
            self.year = None
        else:
            if self.year is None:
                # if we didn't specify all_time, that means we need a current year
                self.year = Year.max()

            try:
                self.season = Season.objects.get(year=self.year)
                if self.season.place_1:
                    self.headline = "Blingabowl {}: {} def. {}".format(
                        self.season.blingabowl,
                        self.season.place_1,
                        self.season.place_2,
                    )
            except Season.DoesNotExist:
                pass  # won't exist for the current season

        self.cache_key = "|".join(map(str, (year, all_time, include_playoffs, week_max)))

    def team_record(self, member):
        if self.all_time:
            return TeamMultiSeasons(
                member.id,
                include_playoffs=self.include_playoffs,
                week_max=self.week_max,
            )
        else:
            return TeamSeason(
                member.id,
                self.year,
                include_playoffs=self.include_playoffs,
                week_max=self.week_max,
            )

    def build_table(self, members, allow_zero_games=False):
        team_records = []

        for member in members:
            team_record = self.team_record(member)

            if len(team_record.games) > 0 or allow_zero_games:
                team_records.append(team_record)

        return sorted(team_records, key=lambda x: (x.win_pct, x.points), reverse=True)

    @fully_cached_property
    def table(self):
        if self.year is not None and self.year > Year.max():
            return []

        members = Member.objects.order_by('first_name', 'last_name')
        allow_zero_games = False

        if self.year is not None and self.year > Week.latest().year:
            members = members.filter(defunct=False)
            allow_zero_games = True

        if self.all_time:
            members = members.filter(defunct=False)

        return self.build_table(members, allow_zero_games=allow_zero_games)

    @fully_cached_property
    def defunct_table(self):
        if not self.all_time:
            return []
        return self.build_table(Member.objects.filter(defunct=True))

    @fully_cached_property
    def href(self):
        if self.year is not None:
            return urlresolvers.reverse_lazy('blingaleague.standings_year', args=(self.year,))
        elif self.all_time:
            getargs = ''
            if self.include_playoffs:
                getargs = '?include_playoffs'

            return "{}{}".format(
                urlresolvers.reverse_lazy('blingaleague.standings_all_time'),
                getargs,
            )

    def team_to_place(self, team):
        for place, team_record in enumerate(self.table):
            if team == team_record.team:
                return place + 1

        return None

    def __str__(self):
        if self.year:
            text = "{} standings".format(self.year)
        else:
            text = 'All-time standings'

        if self.include_playoffs:
            text = "{} (including playoffs)".format(text)

        return text

    def __repr__(self):
        return str(self)


class Week(object):

    def __init__(self, year, week):
        self.year = int(year)
        self.week = int(week)

        self.cache_key = "{}|{}".format(year, week)

    @fully_cached_property
    def games(self):
        games = Game.objects.filter(year=self.year, week=self.week)

        def _sort(game):
            playoff_title_order = {
                BLINGABOWL_TITLE_BASE: 100,
                SEMIFINALS_TITLE_BASE: 90,
                THIRD_PLACE_TITLE_BASE: 80,
                QUARTERFINALS_TITLE_BASE: 70,
                FIFTH_PLACE_TITLE_BASE: 60,
            }

            sorted_titles = sorted(
                playoff_title_order.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for playoff_title, sort_val in sorted_titles:
                if game.playoff_title.startswith(playoff_title):
                    return sort_val

            return 0

        return sorted(games, key=lambda x: (_sort(x), x.winner_score, x.loser_score), reverse=True)

    @fully_cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.week', args=(self.year, self.week))

    @fully_cached_property
    def average_score(self):
        # divide by two because the total_score attribute
        # is made up of both scores in a game
        return mean([g.total_score for g in self.games]) / 2

    @fully_cached_property
    def average_margin(self):
        return mean([g.margin for g in self.games])

    @fully_cached_property
    def previous(self):
        if self.week == 1:
            prev_week = Week(self.year - 1, BLINGABOWL_WEEK)
        else:
            prev_week = Week(self.year, self.week - 1)

        if len(prev_week.games) == 0:
            return None

        return prev_week

    @fully_cached_property
    def next(self):
        if self.week == BLINGABOWL_WEEK:
            next_week = Week(self.year + 1, 1)
        else:
            next_week = Week(self.year, self.week + 1)

        if len(next_week.games) == 0:
            return None

        return next_week

    @fully_cached_property
    def blangums(self):
        if self.week > REGULAR_SEASON_WEEKS:
            return None
        return sorted(self.games, key=lambda x: x.winner_score, reverse=True)[0].winner

    @fully_cached_property
    def slapped_heartbeat(self):
        if self.week > REGULAR_SEASON_WEEKS:
            return None
        return sorted(self.games, key=lambda x: x.loser_score)[0].loser

    @fully_cached_property
    def headline(self):
        if len(self.games) == 0:
            return 'No games yet'

        if self.week > REGULAR_SEASON_WEEKS:
            return self.games[0].title

        return "Team Blangums: {} / Slapped Heartbeat: {}".format(
            self.blangums,
            self.slapped_heartbeat,
        )

    @classmethod
    def latest(cls):
        year, week = Game.objects.all().order_by(
            '-year', '-week',
        ).values_list(
            'year', 'week',
        ).first()
        return cls(year, week)

    def __str__(self):
        return "Week {}, {}".format(self.week, self.year)

    def __repr__(self):
        return str(self)


class Matchup(object):

    def __init__(self, team1_id, team2_id):
        self.team1 = Member.objects.get(id=team1_id)
        self.team2 = Member.objects.get(id=team2_id)

        self.cache_key = "{}|{}".format(team1_id, team2_id)

    @fully_cached_property
    def games(self):
        games = self.team1_wins + self.team2_wins
        return sorted(games, key=lambda x: (x.year, x.week), reverse=True)

    @fully_cached_property
    def team1_wins(self):
        return list(Game.objects.filter(winner=self.team1, loser=self.team2))

    @fully_cached_property
    def team2_wins(self):
        return list(Game.objects.filter(winner=self.team2, loser=self.team1))

    @fully_cached_property
    def team1_count(self):
        return len(self.team1_wins)

    @fully_cached_property
    def team2_count(self):
        return len(self.team2_wins)

    @fully_cached_property
    def record(self):
        return "{}-{}".format(self.team1_count, self.team2_count)

    @fully_cached_property
    def headline(self):
        if self.team1_count == self.team2_count:
            return "All-time series tied, {}-{}".format(self.team1_count, self.team2_count)
        else:
            text = "{} leads all-time series, {}-{}"
            if self.team1_count > self.team2_count:
                return text.format(self.team1, self.team1_count, self.team2_count)
            else:
                return text.format(self.team2, self.team2_count, self.team1_count)

    @fully_cached_property
    def href(self):
        return urlresolvers.reverse_lazy(
            'blingaleague.matchup',
            args=(self.team1.id, self.team2.id),
        )

    @classmethod
    def get_all_for_team(cls, team1_id):
        team2_id_list = Member.objects.all().order_by(
            'defunct', 'first_name', 'last_name',
        ).values_list('id', flat=True)
        return [cls(team1_id, team2_id) for team2_id in team2_id_list]

    def __str__(self):
        return "{} vs. {}".format(self.team1, self.team2)

    def __repr__(self):
        return str(self)


def build_object_cache(obj):
    print("{}: building cache for {}".format(datetime.datetime.now(), obj))
    for attr in dir(obj):
        # just getting the property will cache it if it isn't already
        getattr(obj, attr)


def build_all_objects_cache():

    try:
        all_game_years = Game.objects.order_by('year').values_list('year', flat=True)
        min_year = all_game_years.first()
        max_year = all_game_years.last()

        year_range = range(min_year, max_year + 1)

        for member in Member.objects.all():
            for year in year_range:
                build_object_cache(TeamSeason(member.pk, year))

            for other_member in Member.objects.all():
                build_object_cache(Matchup(member.pk, other_member.pk))

        for year in year_range:
            build_object_cache(Standings(year))

        build_object_cache(Standings(all_time=True))
        build_object_cache(Standings(all_time=True, include_playoffs=True))

    except Exception as e:
        # print if we're in the shell, but don't actually raise
        import traceback
        print(traceback.format_exc())


def rebuild_whole_cache():
    clear_cached_properties()

    build_all_objects_cache()
