import datetime
import decimal
import itertools
import statistics

from collections import defaultdict

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import ordinal, intcomma
from django.core import urlresolvers
from django.core.cache import caches
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db import models

from .utils import int_to_roman, fully_cached_property, clear_cached_properties, \
                   regular_season_weeks, quarterfinals_week, semifinals_week, blingabowl_week


CACHE = caches['blingaleague']

BYE_TEAMS = 2
PLAYOFF_TEAMS = 6
FIRST_SEASON = 2008
EXPANSION_SEASON = 2012

OUTCOME_WIN = 'W'
OUTCOME_LOSS = 'L'
OUTCOME_TIE = 'T'
OUTCOME_ANY = '*'

BLINGABOWL_TITLE_BASE = 'Blingabowl'
SEMIFINALS_TITLE_BASE = 'Semifinals'
QUARTERFINALS_TITLE_BASE = 'Quarterfinals'
THIRD_PLACE_TITLE_BASE = 'Third-Place Game'
FIFTH_PLACE_TITLE_BASE = 'Fifth-Place Game'

PLAYOFF_TITLE_ORDER = [
    BLINGABOWL_TITLE_BASE,
    SEMIFINALS_TITLE_BASE,
    QUARTERFINALS_TITLE_BASE,
    THIRD_PLACE_TITLE_BASE,
    FIFTH_PLACE_TITLE_BASE,
]

ELIMINATION_GAMES = [
    BLINGABOWL_TITLE_BASE,
    SEMIFINALS_TITLE_BASE,
    QUARTERFINALS_TITLE_BASE,
]

MAX_SIMILARITY_SCORE = decimal.Decimal(1000)

MAX_WEEKS_TO_RUN_POSSIBLE_OUTCOMES = 2  # 3+ and it throws an OOM error

POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']

HALF = decimal.Decimal(0.5)
TIE_VALUE = HALF


def position_sort_key(position):
    try:
        return POSITIONS.index(position)
    except ValueError:
        return len(POSITIONS)


def compare_two_scores(score1, score2):
    if score1 > score2:
        return OUTCOME_WIN
    elif score1 < score2:
        return OUTCOME_LOSS
    return OUTCOME_TIE


class ComparableObject(object):

    @property
    def _comparison_attr(self):
        return NotImplementedError('Must be defined by the subclass')

    @fully_cached_property
    def _comparison_val(self):
        return getattr(self, self._comparison_attr)

    def __gt__(self, obj2):
        return self._comparison_val > obj2._comparison_val

    def __ge__(self, obj2):
        return self._comparison_val >= obj2._comparison_val

    def __lt__(self, obj2):
        return self._comparison_val < obj2._comparison_val

    def __le__(self, obj2):
        return self._comparison_val <= obj2._comparison_val

    def __eq__(self, obj2):
        return self._comparison_val == obj2._comparison_val

    def __ne__(self, obj2):
        return self._comparison_val != obj2._comparison_val


class Member(models.Model, ComparableObject):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    nickname = models.CharField(max_length=50, blank=True, null=True)
    defunct = models.BooleanField(default=False)
    email = models.EmailField(blank=True, null=True)
    use_nickname = models.BooleanField(default=False)

    _comparison_attr = 'full_name'

    @property
    def cache_key(self):
        return str(self.pk)

    @fully_cached_property
    def full_name(self):
        if self.use_nickname:
            return "{} \"{}\" {}".format(
                self.first_name,
                self.nickname,
                self.last_name,
            )

        return "{} {}".format(self.first_name, self.last_name)

    @fully_cached_property
    def seasons(self):
        return TeamMultiSeasons(self.id)

    @fully_cached_property
    def seasons_including_playoffs(self):
        return TeamMultiSeasons(self.id, include_playoffs=True)

    def last_x_seasons(self, num_seasons):
        last_season = Season.latest()
        years_range = range(
            last_season.year - num_seasons + 1,
            last_season.year + 1,
        )
        return TeamMultiSeasons(self.id, years=years_range)

    @fully_cached_property
    def blangums_games(self):
        return self.seasons.blangums_games

    @fully_cached_property
    def slapped_heartbeat_games(self):
        return self.seasons.slapped_heartbeat_games

    @fully_cached_property
    def playoff_seasons(self):
        return [
            season for season in self.seasons if season.made_playoffs
        ]

    @fully_cached_property
    def bye_seasons(self):
        return [
            season for season in self.seasons if season.bye
        ]

    @fully_cached_property
    def championship_seasons(self):
        return [
            season for season in self.seasons if season.champion
        ]

    @fully_cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.team', args=(self.id,))

    @fully_cached_property
    def gazette_link(self):
        return "{}{}".format(settings.FULL_SITE_URL, self.href)

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


class Game(models.Model, ComparableObject):
    year = models.IntegerField(db_index=True)
    week = models.IntegerField(db_index=True)
    winner = models.ForeignKey(Member, db_index=True, related_name='games_won')
    loser = models.ForeignKey(Member, db_index=True, related_name='games_lost')
    winner_score = models.DecimalField(max_digits=6, decimal_places=2, db_index=True)
    loser_score = models.DecimalField(max_digits=6, decimal_places=2, db_index=True)
    notes = models.TextField(blank=True, null=True)

    _comparison_attr = 'year_week_id'

    @property
    def cache_key(self):
        return str(self.pk)

    @fully_cached_property
    def year_week_id(self):
        return (self.year, self.week, self.pk)

    @fully_cached_property
    def week_object(self):
        return Week(self.year, self.week)

    @fully_cached_property
    def winner_team_season(self):
        return TeamSeason(self.winner.id, self.year)

    @fully_cached_property
    def loser_team_season(self):
        return TeamSeason(self.loser.id, self.year)

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
        return self.week > regular_season_weeks(self.year)

    @fully_cached_property
    def is_elimination(self):
        return self.is_playoffs and self.playoff_title_base in ELIMINATION_GAMES

    @fully_cached_property
    def playoff_title_base(self):
        if self.is_playoffs:
            previous_week = self.week_object.previous

            winner_last_game = previous_week.team_to_game.get(self.winner)

            if self.week == blingabowl_week(self.year):
                if self.winner == winner_last_game.winner:
                    # blingabowl participants must have won their last game
                    return BLINGABOWL_TITLE_BASE
                else:
                    return THIRD_PLACE_TITLE_BASE
            elif self.week == semifinals_week(self.year):
                if winner_last_game is None or self.winner == winner_last_game.winner:
                    # semifinal participants either won their last game or had a bye
                    return SEMIFINALS_TITLE_BASE
                else:
                    return FIFTH_PLACE_TITLE_BASE
            else:
                return QUARTERFINALS_TITLE_BASE

        return ''

    @fully_cached_property
    def playoff_title(self):
        if self.playoff_title_base:
            if self.playoff_title_base == BLINGABOWL_TITLE_BASE:
                return "{} {}, {}".format(
                    self.playoff_title_base,
                    Postseason.year_to_blingabowl(self.year),
                    self.year,
                )
            else:
                return "{}, {}".format(
                    self.playoff_title_base,
                    self.year,
                )

        return ''

    @fully_cached_property
    def margin(self):
        return self.winner_score - self.loser_score

    @fully_cached_property
    def total_score(self):
        return self.winner_score + self.loser_score

    @fully_cached_property
    def winner_zscore(self):
        return self._zscore(self.winner_score)

    @fully_cached_property
    def loser_zscore(self):
        return self._zscore(self.loser_score)

    def _zscore(self, score):
        return (score - self.week_object.average_score) / self.week_object.stdev_score

    @classmethod
    def all_scores(cls, include_playoffs=False):
        cache_key = "blingaleague_game_all_scores|{}".format(include_playoffs)

        all_scores = CACHE.get(cache_key)

        if all_scores is None:
            all_scores = []

            games = cls.objects.all()

            game_attrs = games.values_list(
                'winner_score',
                'loser_score',
                'year',
                'week',
            )

            for winner_score, loser_score, year, week in game_attrs:
                if not include_playoffs:
                    if week > regular_season_weeks(year):
                        continue

                all_scores.extend([winner_score, loser_score])

            CACHE.set(cache_key, all_scores)

        return all_scores

    @classmethod
    def expected_wins(cls, *game_scores, include_playoffs=False):
        all_scores = cls.all_scores(include_playoffs=include_playoffs)

        all_scores_count = decimal.Decimal(len(all_scores))

        def _win_expectancy(score):
            win_list = list(filter(lambda x: x < score, all_scores))
            tie_list = list(filter(lambda x: x == score, all_scores))
            win_count = len(win_list) + 0.5 * len(tie_list)
            return decimal.Decimal(win_count) / all_scores_count

        return sum(_win_expectancy(score) for score in game_scores)

    def _sequential_team_game(self, team, backwards=False):
        sequential_team_game = None

        week_obj = self.week_object

        while sequential_team_game is None:
            if backwards:
                week_obj = week_obj.previous
            else:
                week_obj = week_obj.next

            if week_obj is None:
                return None

            sequential_team_game = week_obj.team_to_game.get(team)

        return sequential_team_game

    @fully_cached_property
    def winner_previous(self):
        return self._sequential_team_game(self.winner, backwards=True)

    @fully_cached_property
    def winner_next(self):
        return self._sequential_team_game(self.winner)

    @fully_cached_property
    def loser_previous(self):
        return self._sequential_team_game(self.loser, backwards=True)

    @fully_cached_property
    def loser_next(self):
        return self._sequential_team_game(self.loser)

    def _outcome_streak(self, winner=True):
        outcome_attr = 'winner' if winner else 'loser'
        previous_attr = "{}_previous".format(outcome_attr)

        streak = 1

        previous = getattr(self, previous_attr)

        def _get_team(obj):
            return getattr(obj, outcome_attr)

        while previous is not None and (_get_team(self) == _get_team(previous)):
            streak += 1
            previous = getattr(previous, previous_attr)

        return streak

    @fully_cached_property
    def winner_streak(self):
        return self._outcome_streak(winner=True)

    @fully_cached_property
    def loser_streak(self):
        return self._outcome_streak(winner=False)

    def other_weekly_games(self):
        return Game.objects.exclude(pk=self.pk).filter(year=self.year, week=self.week)

    def week_is_full(self):
        other_games_count = self.other_weekly_games().count()

        if (self.year < EXPANSION_SEASON and other_games_count >= 6) or other_games_count >= 7:
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
            if self.year < EXPANSION_SEASON:
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

    @fully_cached_property
    def gazette_str(self):
        return "{} def. {}, {}-{}".format(
            self.winner.nickname,
            self.loser.nickname,
            self.winner_score,
            self.loser_score,
        )

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


class Postseason(models.Model):
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
    def regular_season(self):
        return Season(year=self.year)

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

    @classmethod
    def year_to_blingabowl(cls, year):
        return int_to_roman(year + 1 - FIRST_SEASON)

    @fully_cached_property
    def blingabowl(self):
        return Postseason.year_to_blingabowl(self.year)

    @fully_cached_property
    def robscores(self):
        robscores = defaultdict(lambda: 0)

        for team in self.playoff_results:
            robscores[team] += 1  # all playoff teams get one

            # there are bonuses for finishing in the top three
            if team == self.place_1:
                robscores[team] += 1.0
            elif team == self.place_2:
                robscores[team] += 0.5
            elif team == self.place_3:
                robscores[team] += 0.25

        # regular-season winner and runner-up also get something
        robscores[self.regular_season.standings_table[0].team] += 0.5
        robscores[self.regular_season.standings_table[1].team] += 0.25

        return dict(robscores)

    @fully_cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.single_season', args=(self.year,))

    def team_to_playoff_finish(self, team):
        for place, finish_team in enumerate(self.playoff_results):
            if team == finish_team:
                return place + 1
        return None

    def save(self, **kwargs):
        super().save(**kwargs)
        clear_cached_properties()

    def __str__(self):
        return "{} postseason".format(self.year)

    def __repr__(self):
        return str(self)

    class Meta:
        ordering = ['-year']


class TeamSeason(ComparableObject):
    _comparison_attr = 'year_team'

    is_single_season = True

    def __init__(self, team_id, year, include_playoffs=False, week_max=None):
        self.year = int(year)
        self.team = Member.objects.get(id=team_id)
        if week_max is None:
            if include_playoffs:
                week_max = blingabowl_week(self.year)
            else:
                week_max = regular_season_weeks(self.year)
        self.week_max = week_max

        try:
            self.postseason = Postseason.objects.get(year=self.year)
        except Postseason.DoesNotExist:
            self.postseason = None  # this is ok, it's the current season

        self.cache_key = '|'.join(map(str, (team_id, year, include_playoffs, week_max)))

    @fully_cached_property
    def year_team(self):
        return (self.year, self.team)

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
    def outcome_sequence(self):
        outcome_sequence = []

        for game in self.games:
            if game.winner == self.team:
                outcome_sequence.append(OUTCOME_WIN)
            else:
                outcome_sequence.append(OUTCOME_LOSS)

        return outcome_sequence

    def week_outcome(self, week):
        if week < 1 or week > len(self.games):
            return None
        return self.outcome_sequence[week - 1]

    @fully_cached_property
    def record(self):
        return "{}-{}".format(self.win_count, self.loss_count)

    @fully_cached_property
    def current_streak(self):
        last_game = self.games[-1]

        if self.team == last_game.winner:
            outcome = OUTCOME_WIN
            streak = last_game.winner_streak
        else:
            outcome = OUTCOME_LOSS
            streak = last_game.loser_streak

        streak = min(streak, len(self.games))

        return "{}{}".format(outcome, streak)

    def longest_streak(self, outcome_to_match):
        longest_streak = 0
        running_streak = 0
        for game in self.games:
            outcome = self.week_outcome(game.week)
            if outcome == outcome_to_match:
                running_streak += 1
            else:
                # update longest streak, if necessary
                longest_streak = max(longest_streak, running_streak)
                running_streak = 0

        # one more max() call in case the longest streak ended the season
        return max(longest_streak, running_streak)

    @fully_cached_property
    def longest_winning_streak(self):
        return self.longest_streak(OUTCOME_WIN)

    @fully_cached_property
    def longest_losing_streak(self):
        return self.longest_streak(OUTCOME_LOSS)

    @fully_cached_property
    def win_pct(self):
        if len(self.games) == 0:
            return 0
        return decimal.Decimal(self.win_count) / decimal.Decimal(len(self.games))

    @fully_cached_property
    def points(self):
        return sum(self.game_scores)

    @fully_cached_property
    def points_against(self):
        return sum(self.game_scores_against)

    @fully_cached_property
    def average_score(self):
        return statistics.mean(self.game_scores)

    @fully_cached_property
    def median_score(self):
        return statistics.median(self.game_scores)

    @fully_cached_property
    def min_score(self):
        return min(self.game_scores)

    @fully_cached_property
    def max_score(self):
        return max(self.game_scores)

    @fully_cached_property
    def stdev_score(self):
        return statistics.pstdev(self.game_scores)

    @fully_cached_property
    def average_margin(self):
        return statistics.mean(self.game_margins)

    @fully_cached_property
    def average_margin_win(self):
        if len(self.win_margins) == 0:
            return decimal.Decimal(0)
        return statistics.mean(self.win_margins)

    @fully_cached_property
    def average_margin_loss(self):
        if len(self.loss_margins) == 0:
            return decimal.Decimal(0)
        return statistics.mean(self.loss_margins)

    @classmethod
    def _zscore(cls, value, average, stdev):
        return (value - average) / stdev

    @fully_cached_property
    def zscore_points(self):
        return self._zscore(
            self.points,
            self.season_object.average_team_points,
            self.season_object.stdev_team_points,
        )

    @fully_cached_property
    def zscore_expected_wins(self):
        return self._zscore(
            self.expected_wins,
            self.season_object.average_team_expected_wins,
            self.season_object.stdev_team_expected_wins,
        )

    @fully_cached_property
    def season_object(self):
        return Season(year=self.year, week_max=self.week_max)

    @fully_cached_property
    def place_numeric(self):
        if self.week_max > regular_season_weeks(self.year):
            return self.regular_season.place_numeric
        return self.season_object.team_to_place(self.team)

    @fully_cached_property
    def place(self):
        if self.place_numeric is None:
            return '?'
        return ordinal(self.place_numeric)

    @fully_cached_property
    def playoff_finish_numeric(self):
        if not self.is_single_season:
            return None

        if self.postseason is None:
            return None

        return self.postseason.team_to_playoff_finish(self.team)

    @fully_cached_property
    def playoff_finish(self):
        if self.playoff_finish_numeric == 1:
            return "Blingabowl {} champion".format(self.postseason.blingabowl)

        if self.playoff_finish_numeric is not None:
            return ordinal(self.playoff_finish_numeric)

        return ''

    @fully_cached_property
    def made_playoffs(self):
        regular_season = self.regular_season
        return regular_season.place_numeric <= PLAYOFF_TEAMS and not regular_season.is_partial

    @fully_cached_property
    def missed_playoffs(self):
        regular_season = self.regular_season
        return regular_season.place_numeric > PLAYOFF_TEAMS and not regular_season.is_partial

    @fully_cached_property
    def bye(self):
        regular_season = self.regular_season
        return regular_season.place_numeric <= BYE_TEAMS and not regular_season.is_partial

    @fully_cached_property
    def champion(self):
        if self.postseason is None:
            return False
        return self.team == self.postseason.place_1

    @fully_cached_property
    def game_scores(self):
        win_tuples = [(win.year, win.week, win.winner_score) for win in self.wins]
        loss_tuples = [(loss.year, loss.week, loss.loser_score) for loss in self.losses]
        all_tuples = sorted(win_tuples + loss_tuples)
        return list(map(lambda x: x[2], all_tuples))

    @fully_cached_property
    def game_scores_against(self):
        win_tuples = [(win.year, win.week, win.winner_score) for win in self.losses]
        loss_tuples = [(loss.year, loss.week, loss.loser_score) for loss in self.wins]
        all_tuples = sorted(win_tuples + loss_tuples)
        return list(map(lambda x: x[2], all_tuples))

    @fully_cached_property
    def win_margins(self):
        return sorted(map(lambda x: x.margin, self.wins))

    @fully_cached_property
    def loss_margins(self):
        return sorted(map(lambda x: x.margin, self.losses))

    @fully_cached_property
    def game_margins(self):
        return sorted(self.win_margins + self.loss_margins)

    @fully_cached_property
    def is_partial(self):
        return len(self.games) < regular_season_weeks(self.year)

    @fully_cached_property
    def is_upcoming_season(self):
        return self.season_object.is_upcoming_season and not self.team.defunct

    @fully_cached_property
    def raw_expected_wins_by_game(self):
        return list(map(
            lambda x: Game.expected_wins(x),
            self.game_scores,
        ))

    @fully_cached_property
    def expected_wins_by_game(self):
        return list(map(
            lambda x: self.season_object.expected_wins_scaling_factor * x,
            self.raw_expected_wins_by_game,
        ))

    @fully_cached_property
    def raw_expected_wins(self):
        return sum(self.raw_expected_wins_by_game)

    @fully_cached_property
    def expected_wins(self):
        return min(
            sum(self.expected_wins_by_game),
            decimal.Decimal(len(self.games)),
        )

    @fully_cached_property
    def raw_expected_wins_against(self):
        return Game.expected_wins(*self.game_scores_against)

    @fully_cached_property
    def expected_wins_against(self):
        scaling_factor = self.season_object.expected_wins_scaling_factor
        raw_expected_wins_against = self.raw_expected_wins_against
        expected_wins_against = scaling_factor * raw_expected_wins_against
        return min(
            expected_wins_against,
            decimal.Decimal(len(self.games)),
        )

    @fully_cached_property
    def expected_win_pct_against(self):
        if len(self.games) == 0:
            return 0
        return self.expected_wins_against / len(self.games)

    @fully_cached_property
    def strength_of_schedule(self):
        return (self.expected_win_pct_against - HALF) / HALF

    @fully_cached_property
    def strength_of_schedule_str(self):
        prefix = ''
        if self.strength_of_schedule > 0:
            prefix = '+'
        return "{}{:.1f}%".format(prefix, 100 * self.strength_of_schedule)

    @fully_cached_property
    def expected_wins_luck(self):
        return self.win_count - self.expected_wins

    @fully_cached_property
    def expected_win_pct(self):
        if len(self.games) == 0:
            return 0
        return self.expected_wins / len(self.games)

    @fully_cached_property
    def expected_win_distribution(self):
        if not self.is_single_season:
            # too expensive to calculate for more than one season
            return {}

        if len(self.games) == 0:
            return {}

        expected_wins_by_game = self.expected_wins_by_game
        num_games = len(expected_wins_by_game)
        if num_games > regular_season_weeks(self.year):
            # we only care about this for the regular season
            expected_wins_by_game = self.regular_season.expected_wins_by_game
            num_games = regular_season_weeks(self.year)

        outcome_combos = itertools.product([0, 1], repeat=num_games)

        win_distribution = defaultdict(decimal.Decimal)

        for outcome_combo in outcome_combos:
            win_count = 0
            running_prob = decimal.Decimal(1)
            for i, outcome in enumerate(outcome_combo):
                wp = expected_wins_by_game[i]
                if outcome:
                    win_count += 1
                    running_prob *= wp
                else:
                    running_prob *= (1 - wp)

            win_distribution[win_count] += running_prob

        # for low enough values, it can sometimes dip below zero
        for win_count, probability in win_distribution.items():
            if probability < 0:
                win_distribution[win_count] = 0

        return dict(win_distribution)

    @fully_cached_property
    def _all_play_record(self):
        all_play_record = defaultdict(int)

        for week in range(1, len(self.games) + 1):
            week_obj = Week(self.year, week)

            for outcome, count in week_obj.all_play_record(self.team).items():
                all_play_record[outcome] += count

        return all_play_record

    @fully_cached_property
    def all_play_wins(self):
        return self._all_play_record[OUTCOME_WIN]

    @fully_cached_property
    def all_play_losses(self):
        return self._all_play_record[OUTCOME_LOSS]

    @fully_cached_property
    def all_play_ties(self):
        return self._all_play_record[OUTCOME_TIE]

    @fully_cached_property
    def all_play_win_pct(self):
        wins = decimal.Decimal(self.all_play_wins)
        losses = decimal.Decimal(self.all_play_losses)
        ties = decimal.Decimal(self.all_play_ties)

        total = wins + losses + ties
        if total == 0:
            return 0

        return (wins + HALF * ties) / total

    @fully_cached_property
    def all_play_record_str(self):
        record_parts = [
            self.all_play_wins,
            self.all_play_losses,
        ]

        if self.all_play_ties:
            record_parts.append(self.all_play_ties)

        return '-'.join(map(intcomma, record_parts))

    @fully_cached_property
    def _vs_season_median_record(self):
        vs_season_median_record = defaultdict(int)

        season_median = self.season_object.median_game_score

        for score in self.game_scores:
            outcome = compare_two_scores(score, season_median)
            vs_season_median_record[outcome] += 1

        return vs_season_median_record

    @fully_cached_property
    def vs_season_median_wins(self):
        return self._vs_season_median_record[OUTCOME_WIN]

    @fully_cached_property
    def vs_season_median_losses(self):
        return self._vs_season_median_record[OUTCOME_LOSS]

    @fully_cached_property
    def vs_season_median_ties(self):
        return self._vs_season_median_record[OUTCOME_TIE]

    @fully_cached_property
    def vs_season_median_win_pct(self):
        wins = decimal.Decimal(self.vs_season_median_wins)
        losses = decimal.Decimal(self.vs_season_median_losses)
        ties = decimal.Decimal(self.vs_season_median_ties)

        total = wins + losses + ties
        if total == 0:
            return 0

        return (wins + HALF * ties) / total

    def _vs_score_list(self, score_list):
        record = defaultdict(int)

        for i, score in enumerate(self.game_scores):
            opponent_score = score_list[i]
            outcome = compare_two_scores(score, opponent_score)
            record[outcome] += 1

        return record

    def vs_other_team(self, opponent_id):
        opponent_season = TeamSeason(opponent_id, self.year)
        return self._vs_score_list(opponent_season.game_scores)

    def vs_other_schedule(self, opponent_id):
        opponent_season = TeamSeason(opponent_id, self.year)
        return self._vs_score_list(opponent_season.game_scores_against)

    @fully_cached_property
    def rank_by_week(self):
        rank_by_week = {}

        stats_to_rank = [
            {'attr': 'points', 'name': 'points'},
            {'attr': 'expected_wins', 'name': 'expected wins'},
        ]

        week_max = min(len(self.games), regular_season_weeks(self.year))
        week = 1
        while week <= week_max:
            ts_week = TeamSeason(self.team.id, self.year, week_max=week)
            week_ranks = {
                'place': ts_week.place_numeric,
            }

            for stat in stats_to_rank:
                sorted_table = sorted(
                    Season(self.year, week_max=week).standings_table,
                    key=lambda x: getattr(x, stat['attr']),
                    reverse=True,
                )

                for rank, ts in enumerate(sorted_table, 1):
                    if ts.team == self.team:
                        week_ranks[stat['name']] = rank
                        break

            rank_by_week[week] = week_ranks

            week += 1

        return rank_by_week

    @fully_cached_property
    def blangums_games(self):
        def _is_blangums(game):
            return (game.week_object.blangums == self.team and
                    game.week <= regular_season_weeks(game.year))

        return list(filter(_is_blangums, self.games))

    @fully_cached_property
    def blangums_count(self):
        return len(self.blangums_games)

    @fully_cached_property
    def slapped_heartbeat_games(self):
        def _is_slapped_heartbeat(game):
            return (game.week_object.slapped_heartbeat == self.team and
                    game.week <= regular_season_weeks(self.year))

        return list(filter(_is_slapped_heartbeat, self.games))

    @fully_cached_property
    def slapped_heartbeat_count(self):
        return len(self.slapped_heartbeat_games)

    @fully_cached_property
    def robscore(self):
        if self.postseason is None:
            return 0

        return self.postseason.robscores.get(self.team, 0)

    @fully_cached_property
    def strength_of_schedule_opponent(self):
        previous_season = self.season_object.previous

        if previous_season is None:
            return None

        if self.previous is not None:
            last_year_place = self.previous.place_numeric
            if self.previous.playoff_finish_numeric:
                last_year_place = self.previous.playoff_finish_numeric
        else:
            replaced_teams = set(previous_season.active_teams).difference(
                set(self.season_object.active_teams),
            )

            if len(replaced_teams) != 1:
                raise Exception(
                    "More than 1 candidate that {} replaced: {}".format(
                        self.short_name,
                        replaced_teams,
                    ),
                )

            replaced_team_season = TeamSeason(replaced_teams.pop().id, previous_season.year)

            last_year_place = replaced_team_season.place_numeric
            if replaced_team_season.playoff_finish_numeric:
                last_year_place = replaced_team_season.playoff_finish_numeric

        if last_year_place % 2 == 0:
            opponent_place = last_year_place - 1
        else:
            opponent_place = last_year_place + 1

        return previous_season.post_playoffs_standings[opponent_place - 1].team

    @fully_cached_property
    def has_beaten(self):
        return sorted([game.loser for game in self.wins])

    @fully_cached_property
    def has_lost_to(self):
        return sorted([game.winner for game in self.losses])

    @fully_cached_property
    def has_played(self):
        return sorted(self.has_beaten + self.has_lost_to)

    @fully_cached_property
    def yet_to_play(self):
        yet_to_play = []

        if self.year >= EXPANSION_SEASON:
            full_season_opponents = list(self.season_object.active_teams)

            if len(full_season_opponents) <= regular_season_weeks(self.year):
                full_season_opponents.append(self.strength_of_schedule_opponent)
        else:
            # we know this is in the past
            full_season_opponents = TeamSeason(
                self.team.id, self.year,
            ).has_played

        for opponent in set(full_season_opponents):
            if opponent == self.team:
                continue

            full_count = full_season_opponents.count(opponent)
            this_count = self.has_played.count(opponent)
            diff = full_count - this_count
            if diff > 0:
                yet_to_play.extend(diff * [opponent])

        return sorted(yet_to_play)

    @fully_cached_property
    def weeks_remaining(self):
        return max(0, regular_season_weeks(self.year) - len(self.games))

    @fully_cached_property
    def clinched_playoffs(self):
        if self.is_partial:
            return self.clinched(PLAYOFF_TEAMS)

        return self.made_playoffs

    @fully_cached_property
    def clinched_bye(self):
        if self.is_partial:
            return self.clinched(BYE_TEAMS)

        return self.bye

    @fully_cached_property
    def eliminated_early(self):
        if self.is_partial:
            if self.eliminated_simple:
                return True

            possible_outcomes = self.season_object.possible_final_outcomes
            if possible_outcomes:
                for outcome in possible_outcomes:
                    team_wins = outcome[self.team]
                    sorted_wins = sorted(outcome.values(), reverse=True)

                    if team_wins >= sorted_wins[PLAYOFF_TEAMS - 1]:
                        return False

                return True

        # if it's a complete season, it's not an early elimination
        return False

    def clinched(self, target_place):
        standings_table = self.season_object.standings_table

        if target_place >= len(standings_table):
            # no matter what, every team has clinched at least last place
            return True

        if self.clinched_simple(target_place):
            return True

        possible_outcomes = self.season_object.possible_final_outcomes
        if possible_outcomes:
            for outcome in possible_outcomes:
                team_wins = outcome[self.team]
                sorted_wins = sorted(outcome.values(), reverse=True)

                # don't subtract one because we actually want to measure the place
                # after the target; i.e. to make the playoffs, we need to have more
                # wins than the 7th place team
                if team_wins <= sorted_wins[target_place]:
                    return False

            return True

        return False

    def clinched_simple(self, target_place):
        # don't subtract one because we actually want to measure the place
        # after the target; i.e. to make the playoffs, we need to have more
        # wins than the 7th place team
        target_current_wins = self.season_object.standings_table[target_place].win_count
        max_target_wins = target_current_wins + self.weeks_remaining

        return self.win_count > max_target_wins

    @fully_cached_property
    def eliminated_simple(self):
        max_wins = self.win_count + self.weeks_remaining
        last_playoff_team_wins = self.season_object.standings_table[PLAYOFF_TEAMS - 1].win_count
        return max_wins < last_playoff_team_wins

    @fully_cached_property
    def standings_note(self):
        if self.clinched_bye:
            return ('b', 'clinched bye')
        elif self.clinched_playoffs:
            return ('x', 'clinched playoff spot')
        elif self.eliminated_early:
            return ('e', 'eliminated from playoff contention')

        return None

    @fully_cached_property
    def headline(self):
        if not self.games:
            return 'No games played'

        text = "{}-{} ({:.3f}), {} points, {}".format(
            self.headline_season.win_count,
            self.headline_season.loss_count,
            self.headline_season.win_pct,
            intcomma(self.headline_season.points),
            self.headline_season.place,
        )

        if self.playoff_finish and not self.is_partial:
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
                'description': str(self.regular_season.season_object),
                'href': self.regular_season.season_object.href,
            },
        ]

    @fully_cached_property
    def regular_season(self):
        return TeamSeason(self.team.id, self.year, week_max=regular_season_weeks(self.year))

    @fully_cached_property
    def headline_season(self):
        if self.is_partial:
            return self

        return self.regular_season

    @fully_cached_property
    def most_similar(self):
        if len(self.games) == 0:
            return []

        limit = 10
        similar_seasons = []
        min_score = 900
        while len(similar_seasons) < limit:
            similar_seasons = list(self._filter_similar_seasons(min_score))
            min_score -= 100

        def _ss_display(ss):
            return {
                'season': ss['season'],
                'score': ss['score'],
            }

        sorted_seasons = sorted(similar_seasons, key=lambda x: x['score'], reverse=True)[:limit]
        return list(map(_ss_display, sorted_seasons))

    def similarity_score(self, other_season):
        attr_weights = {
            'win_pct': 50,
            'expected_win_pct': 40,
            'expected_win_pct_against': 10,
        }

        combined_score = 0
        for attr, weight in attr_weights.items():
            # multiply by 2, since it's extremely rare that two seasons are ever
            # more than .500 apart in any pct metric
            attr_diff = 2 * abs(getattr(self, attr) - getattr(other_season, attr))
            attr_score = max(1 - attr_diff, 0)
            combined_score += weight * attr_score

        return MAX_SIMILARITY_SCORE * combined_score / sum(attr_weights.values())

    def _filter_similar_seasons(self, threshold):
        base_season = self
        week_max = len(self.games)

        if week_max > regular_season_weeks(self.year):
            base_season = self.regular_season
            week_max = regular_season_weeks(self.year)

        for season in Season.all():
            for team_id in Member.objects.all().values_list('id', flat=True):
                if team_id == base_season.team.id and season.year == base_season.year:
                    continue

                team_season = TeamSeason(team_id, season.year, week_max=week_max)

                if len(team_season.games) != week_max:
                    continue

                sim_score = base_season.similarity_score(team_season)
                if sim_score >= threshold:
                    yield {'season': team_season, 'score': sim_score}

    @fully_cached_property
    def trades(self):
        trade_dict = {}

        filter_kwargs = {
            'trade__year': self.year,
            'trade__week__lte': self.week_max,
        }

        assets_received = self.team.assets_received.filter(**filter_kwargs)
        assets_sent = self.team.assets_sent.filter(**filter_kwargs)

        for asset in assets_received:
            if asset.trade.id not in trade_dict:
                trade_dict[asset.trade.id] = {
                    'trade': asset.trade,
                    'received': [],
                    'sent': [],
                }

            trade_dict[asset.trade.id]['received'].append(asset)

        for asset in assets_sent:
            trade_dict[asset.trade.id]['sent'].append(asset)

        return sorted(
            trade_dict.values(),
            key=lambda x: x['trade'],
        )

    @fully_cached_property
    def keepers(self):
        return self.team.keepers.filter(year=self.year)

    @classmethod
    def all(cls):
        for season in Season.all():
            for team_id in Member.objects.all().values_list('id', flat=True):
                team_season = cls(team_id, season.year)
                if len(team_season.games) > 0:
                    yield team_season

    @fully_cached_property
    def gazette_standings_str(self):
        gazette_str = "{}. {}, {}, {}".format(
            self.place_numeric,
            self.team.nickname,
            self.record,
            intcomma(self.points),
        )

        if self.standings_note:
            gazette_str = "{} ({})".format(
                gazette_str,
                self.standings_note[0],
            )

        return gazette_str

    @fully_cached_property
    def gazette_postmortem_str(self):
        return "### [{}, {}, {:.2f} expected wins]({})".format(
            self.team,
            self.headline,
            self.expected_wins,
            self.gazette_link,
        )

    @fully_cached_property
    def gazette_link(self):
        return "{}{}".format(settings.FULL_SITE_URL, self.href)

    @fully_cached_property
    def short_name(self):
        return "{} {}".format(self.year, self.team.nickname)

    def __str__(self):
        base_str = "{}, {}".format(self.team, self.year)

        # if we've built a partial season, but it has a full-length season completed
        # we should note this
        extra_str = ''
        if self.is_partial and len(self.games) != len(self.regular_season.games):
            game_count = len(self.games)
            week_str = 'week'
            if game_count != 1:
                week_str = 'weeks'
            extra_str = "(through {} {})".format(game_count, week_str)

        return "{} {}".format(base_str, extra_str).strip()

    def __repr__(self):
        return str(self)


class TeamMultiSeasons(TeamSeason):
    _comparison_attr = 'team'

    is_single_season = False

    def __init__(self, team_id, years=None, include_playoffs=False, week_max=None):
        if years is None:
            years = [season.year for season in Season.all()]
        print(years)

        self.years = sorted(years)
        self.team = Member.objects.get(id=team_id)
        self.include_playoffs = include_playoffs
        self.week_max = week_max

        years_string = ','.join(map(str, self.years))
        self.cache_key = '|'.join(map(str, (team_id, years_string, include_playoffs, week_max)))

    def _sum_seasonal_values(self, prop_name):
        return sum(getattr(ts, prop_name, 0) for ts in self)

    def _extend_seasonal_values(self, prop_name):
        full_list = []
        for team_season in self:
            full_list.extend(getattr(team_season, prop_name, []))
        return full_list

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

            if len(team_season.games) > 0 or team_season.is_upcoming_season:
                team_seasons.append(team_season)

        return team_seasons

    @fully_cached_property
    def first_active_week(self):
        if len(self.games) > 0:
            return min(self.games).week_object
        return None

    @fully_cached_property
    def last_active_week(self):
        if len(self.games) > 0:
            return max(self.games).week_object
        return None

    @fully_cached_property
    def first_active_year(self):
        if self.first_active_week:
            return self.first_active_week.year
        return None

    @fully_cached_property
    def last_active_year(self):
        if self.last_active_week:
            return self.last_active_week.year
        return None

    @fully_cached_property
    def games(self):
        return self._extend_seasonal_values('games')

    @fully_cached_property
    def wins(self):
        return self._extend_seasonal_values('wins')

    @fully_cached_property
    def losses(self):
        return self._extend_seasonal_values('losses')

    @fully_cached_property
    def blangums_games(self):
        return self._extend_seasonal_values('blangums_games')

    @fully_cached_property
    def slapped_heartbeat_games(self):
        return self._extend_seasonal_values('slapped_heartbeat_games')

    @fully_cached_property
    def raw_expected_wins_by_game(self):
        return self._extend_seasonal_values('raw_expected_wins_by_game')

    @fully_cached_property
    def expected_wins_by_game(self):
        return self._extend_seasonal_values('expected_wins_by_game')

    @fully_cached_property
    def raw_expected_wins(self):
        return self._sum_seasonal_values('raw_expected_wins')

    @fully_cached_property
    def expected_wins(self):
        return self._sum_seasonal_values('expected_wins')

    @fully_cached_property
    def raw_expected_wins_against(self):
        return self._sum_seasonal_values('raw_expected_wins_against')

    @fully_cached_property
    def expected_wins_against(self):
        return self._sum_seasonal_values('expected_wins_against')

    @fully_cached_property
    @fully_cached_property
    def _all_play_record(self):
        return {
            OUTCOME_WIN: self.all_play_wins,
            OUTCOME_LOSS: self.all_play_losses,
            OUTCOME_TIE: self.all_play_ties,
        }

    @fully_cached_property
    def all_play_wins(self):
        return self._sum_seasonal_values('all_play_wins')

    @fully_cached_property
    def all_play_losses(self):
        return self._sum_seasonal_values('all_play_losses')

    @fully_cached_property
    def all_play_ties(self):
        return self._sum_seasonal_values('all_play_ties')

    @fully_cached_property
    def _vs_season_median_record(self):
        return {
            OUTCOME_WIN: self.vs_season_median_wins,
            OUTCOME_LOSS: self.vs_season_median_losses,
            OUTCOME_TIE: self.vs_season_median_ties,
        }

    @fully_cached_property
    def vs_season_median_wins(self):
        return self._sum_seasonal_values('vs_season_median_wins')

    @fully_cached_property
    def vs_season_median_losses(self):
        return self._sum_seasonal_values('vs_season_median_losses')

    @fully_cached_property
    def vs_season_median_ties(self):
        return self._sum_seasonal_values('vs_season_median_ties')

    @fully_cached_property
    def robscore(self):
        return self._sum_seasonal_values('robscore')

    @fully_cached_property
    def season_object(self):
        return Season(
            all_time=True,
            include_playoffs=self.include_playoffs,
            week_max=self.week_max,
        )

    @fully_cached_property
    def clinched_playoffs(self):
        return None

    @fully_cached_property
    def clinched_bye(self):
        return None

    @fully_cached_property
    def eliminated_early(self):
        return None

    @fully_cached_property
    def trades(self):
        trades = []

        for season in self:
            trades.extend(season.trades)

        return sorted(
            trades,
            key=lambda x: x['trade'],
            reverse=True,
        )

    @fully_cached_property
    def keepers(self):
        keepers = []

        for season in sorted(self, reverse=True):  # most recent first
            keepers.extend(season.keepers)

        return keepers

    @fully_cached_property
    def championships(self):
        return len([ts for ts in self if ts.champion])

    @fully_cached_property
    def blingabowl_appearances(self):
        return len([ts for ts in self if ts.playoff_finish_numeric == 2])

    @fully_cached_property
    def playoff_appearances(self):
        return len([ts for ts in self if ts.made_playoffs])

    @fully_cached_property
    def regular_season_first_place_finishes(self):
        return len([ts for ts in self if ts.place_numeric == 1])

    @fully_cached_property
    def average_place(self):
        return statistics.mean([ts.place_numeric for ts in self])

    @fully_cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.team', args=(self.team.id,))

    def __iter__(self):
        for team_season in self.team_seasons:
            yield team_season

    @classmethod
    def all(cls):
        for team_id in Member.objects.all().values_list('id', flat=True):
            team_multi_season = cls(team_id)
            if len(team_multi_season.games) > 0:
                yield team_multi_season

    @fully_cached_property
    def short_name(self):
        return "{}-{} {}".format(
            self.first_active_year,
            self.last_active_year,
            self.team.nickname,
        )

    def __str__(self):
        return "{}, {}-{}".format(
            self.team,
            self.first_active_year,
            self.last_active_year,
        )

    def __repr__(self):
        return str(self)


class Season(ComparableObject):
    _comparison_attr = 'year'

    def __init__(self, year=None, all_time=False, include_playoffs=False, week_max=None):
        self.year = year
        self.all_time = all_time
        self.include_playoffs = include_playoffs

        self.week_max = week_max
        if self.week_max is None and not self.include_playoffs:
            # only time we don't want a week_max is if
            # playoffs are explicitly included
            self.week_max = regular_season_weeks(self.year)

        if self.all_time:
            self.year = None
        else:
            if self.year is None:
                raise ValueError('Must specify a year or all_time must be True')

        self.cache_key = "|".join(map(str, (year, all_time, include_playoffs, week_max)))

    @fully_cached_property
    def postseason(self):
        try:
            return Postseason.objects.get(year=self.year)
        except Postseason.DoesNotExist:
            return None  # won't exist for in-progress seasons

    @fully_cached_property
    def all_games(self):
        all_games = Game.objects.all()

        if self.year is not None:
            all_games = all_games.filter(year=self.year)

        if self.week_max is not None:
            all_games = all_games.filter(week__lte=self.week_max)

        return all_games

    @fully_cached_property
    def total_wins(self):
        return self.all_games.count()

    @fully_cached_property
    def weeks_with_games(self):
        if not self.all_games:
            return 0

        return max(self.all_games.values_list('week', flat=True))

    @fully_cached_property
    def weeks(self):
        return [Week(self.year, week + 1) for week in range(self.weeks_with_games)]

    @fully_cached_property
    def all_game_scores(self):
        all_scores = []
        for winner_score, loser_score in self.all_games.values_list('winner_score', 'loser_score'):
            all_scores.extend([winner_score, loser_score])
        return all_scores

    @fully_cached_property
    def average_game_score(self):
        return statistics.mean(self.all_game_scores)

    @fully_cached_property
    def stdev_game_score(self):
        return statistics.pstdev(self.all_game_scores)

    @fully_cached_property
    def median_game_score(self):
        return statistics.median(self.all_game_scores)

    @fully_cached_property
    def average_team_points(self):
        return statistics.mean(map(lambda x: x.points, self.standings_table))

    @fully_cached_property
    def stdev_team_points(self):
        return statistics.pstdev(map(lambda x: x.points, self.standings_table))

    @fully_cached_property
    def average_team_expected_wins(self):
        return statistics.mean(map(lambda x: x.expected_wins, self.standings_table))

    @fully_cached_property
    def stdev_team_expected_wins(self):
        return statistics.pstdev(map(lambda x: x.expected_wins, self.standings_table))

    @fully_cached_property
    def total_raw_expected_wins(self):
        return Game.expected_wins(*self.all_game_scores)

    @fully_cached_property
    def expected_wins_scaling_factor(self):
        # make sure we aren't including playoff games in the normalization
        if self.weeks_with_games > regular_season_weeks(self.year):
            return self.regular_season.expected_wins_scaling_factor

        scaling_factor = 1
        if self.total_raw_expected_wins > 0:
            scaling_factor = (
                decimal.Decimal(self.total_wins) / decimal.Decimal(self.total_raw_expected_wins)
            )

        return scaling_factor

    @fully_cached_property
    def champion(self):
        if self.postseason is None:
            return None

        return TeamSeason(self.postseason.place_1.id, self.year)

    @fully_cached_property
    def first_place(self):
        return self.standings_table[0]

    def _most_by_attr(self, attr):
        return sorted(
            self.standings_table,
            key=lambda x: getattr(x, attr),
            reverse=True,
        )[0]

    @fully_cached_property
    def most_points(self):
        return self._most_by_attr('points')

    @fully_cached_property
    def most_expected_wins(self):
        return self._most_by_attr('expected_wins')

    def _team_season(self, team):
        if self.all_time:
            return TeamMultiSeasons(
                team.id,
                include_playoffs=self.include_playoffs,
                week_max=self.week_max,
            )
        else:
            return TeamSeason(
                team.id,
                self.year,
                include_playoffs=self.include_playoffs,
                week_max=self.week_max,
            )

    def _build_standings_table(self, teams):
        team_seasons = []

        for team in teams:
            team_season = self._team_season(team)

            if len(team_season.games) > 0 or self.is_upcoming_season:
                team_seasons.append(team_season)

        if self.week_max is not None and self.week_max > regular_season_weeks(self.year):
            return sorted(
                team_seasons,
                key=lambda x: (x.regular_season.win_pct, x.regular_season.points),
                reverse=True,
            )

        return sorted(team_seasons, key=lambda x: (x.win_pct, x.points), reverse=True)

    @fully_cached_property
    def standings_table(self):
        return self._build_standings_table(self.active_teams)

    @fully_cached_property
    def defunct_standings_table(self):
        if not self.all_time:
            return []

        return self._build_standings_table(Member.objects.filter(defunct=True))

    @fully_cached_property
    def active_teams(self):
        if self.is_upcoming_season or self.all_time:
            return Member.objects.filter(defunct=False).order_by('first_name', 'last_name')

        teams = set()
        for game in Game.objects.filter(year=self.year):
            teams.add(game.winner)
            teams.add(game.loser)

        return sorted(teams)

    @fully_cached_property
    def alpha_team_seasons(self):
        if self.standings_table:
            return sorted(
                self.standings_table,
                key=lambda x: x.team,
            )

        return [TeamSeason(team.id, self.year) for team in self.active_teams]

    @fully_cached_property
    def post_playoffs_standings(self):
        if not self.champion:
            return []

        def _post_playoffs_sort(team_season):
            if team_season.playoff_finish_numeric:
                return team_season.playoff_finish_numeric
            return team_season.place_numeric

        return sorted(
            self.standings_table,
            key=_post_playoffs_sort,
        )

    @fully_cached_property
    def is_upcoming_season(self):
        return self.year is not None and self.year > Week.latest().year

    @fully_cached_property
    def is_partial(self):
        if self.all_time:
            return True

        if not self.standings_table:
            # edge case where season hasn't started yet
            return True

        for team_season in self.standings_table:
            if team_season.is_partial:
                return True

        return False

    @fully_cached_property
    def regular_season(self):
        if self.all_time:
            return None

        return Season(year=self.year)

    @fully_cached_property
    def playoff_bracket(self):
        if self.is_partial:
            return []

        return [
            self._playoff_bracket_week(quarterfinals_week(self.year)),
            self._playoff_bracket_week(semifinals_week(self.year)),
            self._playoff_bracket_week(blingabowl_week(self.year)),
        ]

    def _playoff_bracket_week(self, week):
        if self.is_partial:
            return {}

        week_object = Week(self.year, week)
        if not week_object.is_playoffs:
            return {}

        # if the specified week_max is during the playoffs,
        # we will want to act like games that week haven't happened yet
        omit_week_results = False
        if self.week_max > regular_season_weeks(self.year) and week > self.week_max:
            omit_week_results = True

        games_to_ignore = (THIRD_PLACE_TITLE_BASE, FIFTH_PLACE_TITLE_BASE)
        games = []
        if len(week_object.games) > 0 and not omit_week_results:
            for game in week_object.games:
                if game.playoff_title_base in games_to_ignore:
                    continue

                games.append(
                    sorted(
                        (
                            {
                                'team_season': game.winner_team_season,
                                'seed': game.winner_team_season.place_numeric,
                                'score': game.winner_score,
                                'is_winner': True,
                            },
                            {
                                'team_season': game.loser_team_season,
                                'seed': game.loser_team_season.place_numeric,
                                'score': game.loser_score,
                            },
                        ),
                        key=lambda x: x['seed'],
                    ),
                )
        elif week == quarterfinals_week(self.year):
            seed_pairs = [(3, 6), (4, 5)]
            for seed1, seed2 in seed_pairs:
                games.append(
                    (
                        {
                            'team_season': self.standings_table[seed1 - 1],
                            'seed': seed1,
                        },
                        {
                            'team_season': self.standings_table[seed2 - 1],
                            'seed': seed2,
                        },
                    ),
                )
        else:
            last_week_winners = []
            if week_object.previous is not None:
                for game in week_object.previous.games:
                    if game.playoff_title_base in games_to_ignore:
                        continue

                    last_week_winners.append(game.winner_team_season)

            if week == semifinals_week(self.year):
                bye_teams = self.standings_table[:BYE_TEAMS]
                last_week_winners = sorted(
                    last_week_winners,
                    key=lambda x: x.place_numeric,
                    reverse=True,
                )

                if last_week_winners:
                    for i, team_season in enumerate(bye_teams):
                        games.append(
                            (
                                {
                                    'team_season': team_season,
                                    'seed': team_season.place_numeric,
                                },
                                {
                                    'team_season': last_week_winners[i],
                                    'seed': last_week_winners[i].place_numeric,
                                },
                            ),
                        )
                else:
                    # if there are no quarterfinals winners yet, we only know the bye teams
                    games = [
                        (
                            {'team_season': bye_teams[0], 'seed': bye_teams[0].place_numeric},
                            {},
                        ),
                        (
                            {'team_season': bye_teams[1], 'seed': bye_teams[1].place_numeric},
                            {},
                        ),
                    ]
            else:
                # it's Blingabowl week
                last_week_winners = sorted(
                    last_week_winners,
                    key=lambda x: x.place_numeric,
                )

                if last_week_winners:
                    games = [
                        (
                            {
                                'team_season': last_week_winners[0],
                                'seed': last_week_winners[0].place_numeric,
                            },
                            {
                                'team_season': last_week_winners[1],
                                'seed': last_week_winners[1].place_numeric,
                            },
                        ),
                    ]
                else:
                    games = [({}, {})]

        return {
            'week': week_object,
            'games': sorted(
                games,
                key=lambda x: x[0].get('seed'),
            ),
        }

    @fully_cached_property
    def possible_final_outcomes(self):
        if self.is_upcoming_season or self.all_time:
            return None

        remaining_games = set()
        current_win_counts = {}

        for team_season in self.standings_table:
            current_win_counts[team_season.team] = team_season.win_count

            for opponent in team_season.yet_to_play:
                game_tuple = tuple(sorted((team_season.team, opponent)))
                remaining_games.add(game_tuple)

        remaining_games = list(remaining_games)

        num_games = len(remaining_games)

        max_games_to_run = MAX_WEEKS_TO_RUN_POSSIBLE_OUTCOMES * len(self.standings_table) / 2

        if num_games > max_games_to_run:
            return None

        outcome_combos = itertools.product([0, 1], repeat=num_games)

        possible_outcomes = []

        for outcome_combo in outcome_combos:
            win_counts = current_win_counts.copy()
            for i, outcome in enumerate(outcome_combo):
                winner = remaining_games[i][outcome]
                win_counts[winner] += 1

            possible_outcomes.append(win_counts)

        return possible_outcomes

    @fully_cached_property
    def keepers(self):
        return Keeper.objects.filter(
            year=self.year,
        ).order_by(
            'team',
        )

    @fully_cached_property
    def trades(self):
        return Trade.objects.filter(
            year=self.year,
            week__lte=self.week_max,
        ).order_by(
            'week', 'date',
        )

    @classmethod
    def all(cls, **kwargs):
        all_years = set(Game.objects.all().values_list('year', flat=True))
        all_years.update(set(Keeper.objects.all().values_list('year', flat=True)))
        all_years.update(set(Trade.objects.all().values_list('year', flat=True)))

        return [
            cls(year=year, **kwargs) for year in all_years
        ]

    @classmethod
    def min(cls):
        return min(cls.all())

    @classmethod
    def max(cls):
        return max(cls.all())

    @classmethod
    def latest(cls, week_max=None):
        return cls.max()

    @fully_cached_property
    def previous(self):
        prev_year = self.year - 1

        if prev_year < Season.min().year:
            return None

        return Season(year=prev_year)

    @fully_cached_property
    def next(self):
        next_year = self.year + 1

        if next_year > Season.max().year:
            return None

        return Season(year=next_year)

    @fully_cached_property
    def href(self):
        if self.year is not None:
            getargs = ''
            if self.week_max is not None and self.week_max != regular_season_weeks(self.year):
                getargs = "?week_max={}".format(self.week_max)

            return "{}{}".format(
                urlresolvers.reverse_lazy('blingaleague.single_season', args=(self.year,)),
                getargs,
            )

        elif self.all_time:
            getargs = ''
            if self.include_playoffs:
                getargs = '?include_playoffs'

            return "{}{}".format(
                urlresolvers.reverse_lazy('blingaleague.all_time'),
                getargs,
            )

    def team_to_place(self, team):
        for place, team_season in enumerate(self.standings_table, 1):
            if team == team_season.team:
                return place

        return None

    @fully_cached_property
    def gazette_str(self):
        return '\n'.join(
            [ts.gazette_standings_str for ts in self.standings_table],
        )

    @fully_cached_property
    def gazette_link(self):
        return "{}{}".format(
            settings.FULL_SITE_URL,
            self.href,
        )

    @fully_cached_property
    def headline(self):
        # if the specified week_max is during the playoffs,
        # but doesn't include the Blingabowl week,
        # don't populate the headline
        if regular_season_weeks(self.year) < self.week_max < blingabowl_week(self.year):
            return None

        if self.postseason is not None and self.postseason.place_1:
            return "Blingabowl {}: {} def. {}".format(
                self.postseason.blingabowl,
                self.postseason.place_1,
                self.postseason.place_2,
            )

        return None

    def __str__(self):
        if self.year:
            text = "{} season".format(self.year)
        else:
            text = 'All-time'

        if self.include_playoffs:
            text = "{} (including playoffs)".format(text)

        return text

    def __repr__(self):
        return str(self)


class Week(ComparableObject):
    _comparison_attr = 'year_week'

    def __init__(self, year, week):
        self.year = int(year)
        self.week = int(week)

        self.cache_key = "{}|{}".format(year, week)

    @fully_cached_property
    def year_week(self):
        return (self.year, self.week)

    @fully_cached_property
    def is_playoffs(self):
        return self.week > regular_season_weeks(self.year)

    @fully_cached_property
    def games(self):
        games = Game.objects.filter(year=self.year, week=self.week)

        def _sort(game):
            try:
                return PLAYOFF_TITLE_ORDER.index(game.playoff_title_base)
            except ValueError:
                return len(PLAYOFF_TITLE_ORDER)

        return sorted(
            games,
            key=lambda x: (
                -1 * _sort(x),  # _sort defined to support ascending sort
                x.winner_score,
                x.loser_score,
            ),
            reverse=True,
        )

    @fully_cached_property
    def season_object(self):
        return Season(self.year)

    @fully_cached_property
    def trades(self):
        return Trade.objects.filter(
            year=self.year,
            week=self.week,
        ).order_by('-date')

    @fully_cached_property
    def average_score(self):
        return statistics.mean([s['score'] for s in self.team_scores])

    @fully_cached_property
    def average_margin(self):
        return statistics.mean([g.margin for g in self.games])

    @fully_cached_property
    def stdev_score(self):
        return statistics.pstdev([s['score'] for s in self.team_scores])

    @fully_cached_property
    def expected_wins_scaling_factor(self):
        raw_expected_wins = 0
        for game in self.games:
            raw_expected_wins += Game.expected_wins(game.winner_score, game.loser_score)

        return len(self.games) / raw_expected_wins

    @fully_cached_property
    def team_scores(self):
        team_scores = []

        for game in self.games:
            team_scores.extend([
                {
                    'team': game.winner,
                    'score': game.winner_score,
                },
                {
                    'team': game.loser,
                    'score': game.loser_score,
                },
            ])

        return team_scores

    @fully_cached_property
    def team_scores_sorted(self):
        return sorted(
            self.team_scores,
            key=lambda x: x['score'],
            reverse=True,
        )

    @fully_cached_property
    def team_to_score(self):
        team_to_score = {}
        for i, team_score in enumerate(self.team_scores_sorted, 1):
            team_to_score[team_score['team']] = team_score['score']
        return team_to_score

    @fully_cached_property
    def team_to_game(self):
        team_to_game = {}
        for game in self.games:
            team_to_game[game.winner] = game
            team_to_game[game.loser] = game
        return team_to_game

    def all_play_record(self, team):
        all_play_record = defaultdict(int)

        score_to_compare = self.team_to_score[team]
        for team_score in self.team_scores:
            if team_score['team'] == team:
                continue

            if team_score['score'] < score_to_compare:
                all_play_record[OUTCOME_WIN] += 1
            elif team_score['score'] == score_to_compare:
                all_play_record[OUTCOME_TIE] += 1
            else:
                all_play_record[OUTCOME_LOSS] += 1

        return all_play_record

    @fully_cached_property
    def blangums(self):
        if self.week > regular_season_weeks(self.year):
            return None
        return self.team_scores_sorted[0]['team']

    @fully_cached_property
    def slapped_heartbeat(self):
        if self.week > regular_season_weeks(self.year):
            return None
        return self.team_scores_sorted[-1]['team']

    @fully_cached_property
    def headline(self):
        if len(self.games) == 0:
            return 'No games yet'

        if self.is_playoffs:
            return self.games[0].title

        return "Team Blangums: {} / Slapped Heartbeat: {}".format(
            self.blangums,
            self.slapped_heartbeat,
        )

    @fully_cached_property
    def bracket_headline(self):
        return self.week_to_title(self.year, self.week)

    @classmethod
    def week_to_title(self, year, week):
        special_weeks = {
            quarterfinals_week(year): QUARTERFINALS_TITLE_BASE,
            semifinals_week(year): SEMIFINALS_TITLE_BASE,
            blingabowl_week(year): "{} {}".format(
                BLINGABOWL_TITLE_BASE,
                Postseason.year_to_blingabowl(year),
            ),
        }

        if week in special_weeks:
            return special_weeks[week]

        return "Week {}".format(week)

    @fully_cached_property
    def gazette_str(self):
        return '\n\n'.join(
            ["### {}:".format(game.gazette_str) for game in self.games],
        )

    @fully_cached_property
    def gazette_link(self):
        week_url = urlresolvers.reverse_lazy(
            'blingaleague.week',
            args=(self.year, self.week),
        )

        return "{}{}".format(
            settings.FULL_SITE_URL,
            week_url,
        )

    @fully_cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.week', args=(self.year, self.week))

    @fully_cached_property
    def previous(self):
        if self.week == 1:
            prev_week = Week(self.year - 1, blingabowl_week(self.year))
        else:
            prev_week = Week(self.year, self.week - 1)

        if len(prev_week.games) == 0:
            return None

        return prev_week

    @fully_cached_property
    def next(self):
        if self.week == blingabowl_week(self.year):
            next_week = Week(self.year + 1, 1)
        else:
            next_week = Week(self.year, self.week + 1)

        if len(next_week.games) == 0:
            return None

        return next_week

    @fully_cached_property
    def level_up_links(self):
        return [
            {
                'description': str(self.season_object),
                'href': self.season_object.href,
            },
        ]

    @classmethod
    def latest(cls):
        return cls.all()[-1]

    @classmethod
    def all(cls):
        all_weeks = []

        year_week_combos = set(Game.objects.all().values_list(
            'year', 'week',
        ))
        for year, week in sorted(year_week_combos):
            all_weeks.append(cls(year, week))

        return all_weeks

    @classmethod
    def regular_season_week_list(cls):
        return list(
            filter(
                lambda x: x.week <= regular_season_weeks(x.year),
                cls.all(),
            ),
        )

    @classmethod
    def playoff_week_list(cls):
        return list(
            filter(
                lambda x: x.week >= quarterfinals_week(x.year),
                cls.all(),
            ),
        )

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
    def trades(self):
        trades = set()

        for asset in TradedAsset.objects.filter(receiver=self.team1):
            if self.team2.id in asset.trade.team_ids:
                trades.add(asset.trade)

        return sorted(
            trades,
            key=lambda x: (x.year, x.week, x.date),
            reverse=True,
        )

    @fully_cached_property
    def headline(self):
        if self.team1_count == self.team2_count:
            return "All-time series tied, {}-{}".format(self.team1_count, self.team2_count)
        else:
            text = "{} leads all-time series, {}-{}"
            if self.team1_count > self.team2_count:
                return text.format(self.team1.nickname, self.team1_count, self.team2_count)
            else:
                return text.format(self.team2.nickname, self.team2_count, self.team1_count)

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


class Trade(models.Model, ComparableObject):
    year = models.IntegerField(db_index=True)
    week = models.IntegerField(db_index=True)
    date = models.DateField(default=None, db_index=True)

    _comparison_attr = 'year_week_date'

    @fully_cached_property
    def year_week_date(self):
        return (
            self.year,
            self.week,
            self.date,
        )

    @fully_cached_property
    def public_id(self):
        date_str = self.date.strftime('%Y%m%d')
        team_id_str = ''.join(
            map(
                lambda x: "{:02}".format(x),
                sorted(self.team_ids),
            ),
        )
        return "{}.{}".format(date_str, team_id_str)

    @fully_cached_property
    def week_object(self):
        return Week(self.year, self.week)

    @fully_cached_property
    def teams(self):
        teams = set()
        for asset in self.traded_assets.all():
            teams.add(asset.receiver)
            teams.add(asset.sender)
        return teams

    @fully_cached_property
    def team_ids(self):
        return set(map(lambda x: x.id, self.teams))

    @fully_cached_property
    def teams_str(self):
        if self.teams:
            return ' and '.join(
                sorted(
                    map(lambda x: x.nickname, self.teams),
                ),
            )

        return 'unknown teams'

    @fully_cached_property
    def description(self):
        return "Trade between {}".format(self.teams_str)

    @fully_cached_property
    def grouped_assets(self):
        assets_by_receiver = defaultdict(list)
        for asset in self.traded_assets.all():
            assets_by_receiver[asset.receiver].append(asset)

        grouped_assets = []
        for team in sorted(self.teams):
            grouped_assets.append({
                'team': team,
                'assets_received': assets_by_receiver[team],
            })

        return grouped_assets

    @classmethod
    def most_recent(cls):
        most_recent = []

        latest_week = Week.latest()

        for trade in cls.objects.order_by('-year', '-week'):
            if trade.week_object < latest_week:
                break
            most_recent.append(trade)

        return most_recent

    @fully_cached_property
    def href(self):
        return urlresolvers.reverse_lazy('blingaleague.trade', args=(self.id,))

    def save(self, **kwargs):
        super().save(**kwargs)
        clear_cached_properties()

    def __str__(self):
        return "{}, {} ({})".format(
            self.description,
            self.week_object,
            self.date.strftime('%Y-%m-%d'),
        )

    def __repr__(self):
        return str(self)

    class Meta:
        ordering = ['-year', '-week', '-date']


class TradedAsset(models.Model):
    trade = models.ForeignKey(Trade, db_index=True, related_name='traded_assets')
    receiver = models.ForeignKey(Member, db_index=True, related_name='assets_received')
    sender = models.ForeignKey(Member, db_index=True, related_name='assets_sent')
    name = models.CharField(max_length=200)
    keeper_eligible = models.BooleanField(default=True)
    keeper_cost = models.IntegerField(blank=True, null=True)
    is_draft_pick = models.BooleanField(default=False)
    position = models.CharField(
        blank=True,
        null=True,
        max_length=10,
        choices=[(p, p) for p in POSITIONS],
    )

    @fully_cached_property
    def keeper_cost_str(self):
        if self.is_draft_pick:
            return ''

        if self.keeper_eligible:
            if self.keeper_cost is None:
                return ''
            else:
                return "keeper cost: {}".format(
                    ordinal(self.keeper_cost),
                )
        else:
            return 'ineligible to be kept'

    @fully_cached_property
    def position_display(self):
        if self.position:
            return self.position

        if self.is_draft_pick:
            return 'Pick'

        return ''

    def save(self, **kwargs):
        super().save(**kwargs)
        clear_cached_properties()

    def __str__(self):
        return "{}, Traded from {} to {}, {} ({})".format(
            self.name,
            self.sender.nickname,
            self.receiver.nickname,
            self.trade.week_object,
            self.trade.date.strftime('%Y-%m-%d'),
        )

    def __repr__(self):
        return str(self)

    class Meta:
        ordering = ['trade', 'sender', 'receiver', 'keeper_cost', 'name']


class Keeper(models.Model, ComparableObject):
    name = models.CharField(max_length=200)
    position = models.CharField(
        max_length=10,
        choices=[(p, p) for p in POSITIONS],
    )
    year = models.IntegerField(db_index=True)
    team = models.ForeignKey(Member, db_index=True, related_name='keepers')
    round = models.IntegerField()
    times_kept = models.IntegerField()

    _comparison_attr = 'name_year'

    @fully_cached_property
    def name_year(self):
        return (
            self.name,
            self.year,
        )

    def save(self, **kwargs):
        super().save(**kwargs)
        clear_cached_properties()

    def __str__(self):
        return "{} ({}, {}, {} round)".format(
            self.name,
            self.team.nickname,
            self.year,
            ordinal(self.round),
        )

    def __repr__(self):
        return str(self)

    class Meta:
        ordering = ['year', 'round', 'team', 'name']


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
            build_object_cache(Season(year))

        build_object_cache(Season(all_time=True))
        build_object_cache(Season(all_time=True, include_playoffs=True))

    except Exception:
        # print if we're in the shell, but don't actually raise
        import traceback
        print(traceback.format_exc())


def rebuild_whole_cache():
    clear_cached_properties()

    build_all_objects_cache()
