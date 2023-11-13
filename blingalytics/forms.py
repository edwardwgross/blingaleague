from django import forms

from django.core.validators import MinValueValidator, MaxValueValidator

from blingaleague.models import Member, Season, BLINGABOWL_TITLE_BASE, \
                                SEMIFINALS_TITLE_BASE, QUARTERFINALS_TITLE_BASE, \
                                THIRD_PLACE_TITLE_BASE, FIFTH_PLACE_TITLE_BASE, \
                                POSITIONS


CHOICE_YES = 'yes'
CHOICE_NO = 'no'

CHOICE_BLANGUMS = 'team_blangums'
CHOICE_SLAPPED_HEARTBEAT = 'slapped_heartbeat'

CHOICE_WINS = 'wins'
CHOICE_LOSSES = 'losses'

CHOICE_REGULAR_SEASON = 'regular'
CHOICE_PLAYOFFS = 'playoffs'

CHOICE_MADE_PLAYOFFS = 'made_playoffs'
CHOICE_MISSED_PLAYOFFS = 'missed_playoffs'

CHOICE_CLINCHED_BYE = 'clinched_bye'
CHOICE_CLINCHED_PLAYOFFS = 'clinched_playoffs'
CHOICE_ELIMINATED_EARLY = 'eliminated_early'

CHOICES_PLAYOFF_GAME_TYPE = (
    BLINGABOWL_TITLE_BASE,
    SEMIFINALS_TITLE_BASE,
    QUARTERFINALS_TITLE_BASE,
    THIRD_PLACE_TITLE_BASE,
    FIFTH_PLACE_TITLE_BASE,
)

CHOICE_MATCHING_ASSETS_ONLY = 'matching_assets'


def _yes_no_field(label):
    return forms.TypedChoiceField(
        required=False,
        label=label,
        widget=forms.RadioSelect,
        choices=[
            ('', 'Any'),
            (CHOICE_YES, 'Yes'),
            (CHOICE_NO, 'No'),
        ],
    )


def _positive_integer_field(**kwargs):
    kwargs.update(validators=[MinValueValidator(1)])
    return forms.IntegerField(**kwargs)


def _year_field(prefix=None):
    label = 'Year'
    if prefix:
        label = prefix.strip() + ' Year'

    return forms.IntegerField(
        required=False,
        label=label,
        validators=[
            MinValueValidator(Season.min().year),
            MaxValueValidator(Season.max().year),
        ],
    )


def _start_year_field():
    return _year_field('Start')


def _end_year_field():
    return _year_field('End')


def _teams_multiple_choice_field(label='Team'):
    return forms.TypedMultipleChoiceField(
        required=False,
        label=label,
        widget=forms.CheckboxSelectMultiple,
        choices=[(m.id, m) for m in Member.objects.all()],
        coerce=int,
    )


def _positions_multiple_choice_field(label='Position'):
    return forms.TypedMultipleChoiceField(
        required=False,
        label=label,
        widget=forms.CheckboxSelectMultiple,
        choices=[(p, p) for p in POSITIONS],
    )


class ExpectedWinsCalculatorForm(forms.Form):
    score = forms.DecimalField(required=False, label='Score', decimal_places=2)
    year = _positive_integer_field(required=False, label='Year')

    def is_valid(self):
        if not super().is_valid():
            return False

        year = self.cleaned_data['year']
        if year is not None:
            min_year = Season.min().year
            max_year = Season.max().year
            if (year < min_year) or (year > max_year):
                self.add_error(
                    None,
                    "Year must be between {} and {}".format(min_year, max_year),
                )
                return False

        return True


class BaseFinderForm(forms.Form):

    filter_threshold = 2

    def is_valid(self):
        if not super().is_valid():
            return False

        # if the values are valid, now we need to make sure we've provided
        # at least a reasonable amount of filters
        unfiltered_values = (None, False, '', [], [''])
        filtered_fields = filter(lambda x: x[1] not in unfiltered_values, self.cleaned_data.items())
        if len(list(filtered_fields)) < self.filter_threshold:
            self.add_error(
                None,
                "You must filter on at least {} field(s) to see results".format(
                    self.filter_threshold,
                ),
            )
            return False

        return True


class GameFinderForm(BaseFinderForm):
    year_min = _start_year_field()
    year_max = _end_year_field()
    week_min = _positive_integer_field(required=False, label='Start Week')
    week_max = _positive_integer_field(required=False, label='End Week')
    week_type = forms.TypedChoiceField(
        required=False,
        label='Game Type',
        widget=forms.RadioSelect,
        choices=[
            ('', 'Any'),
            (CHOICE_REGULAR_SEASON, 'Regular season only'),
            (CHOICE_PLAYOFFS, 'Playoffs only'),
        ],
    )
    playoff_game_types = forms.TypedMultipleChoiceField(
        required=False,
        label='Playoff Game Type',
        widget=forms.CheckboxSelectMultiple,
        choices=[(c, c) for c in CHOICES_PLAYOFF_GAME_TYPE],
    )
    teams = _teams_multiple_choice_field()
    awards = forms.TypedMultipleChoiceField(
        required=False,
        label='Weekly Awards',
        widget=forms.CheckboxSelectMultiple,
        choices=[
            (CHOICE_BLANGUMS, 'Team Blangums'),
            (CHOICE_SLAPPED_HEARTBEAT, 'Slapped Heartbeat'),
        ],
    )
    score_min = forms.DecimalField(required=False, label='Minimum Score', decimal_places=2)
    score_max = forms.DecimalField(required=False, label='Maximum Score', decimal_places=2)
    margin_min = forms.DecimalField(required=False, label='Minimum Margin', decimal_places=2)
    margin_max = forms.DecimalField(required=False, label='Maximum Margin', decimal_places=2)
    outcome = forms.TypedChoiceField(
        required=False,
        label='Winner / Loser',
        widget=forms.RadioSelect,
        choices=[
            ('', 'Either winner or loser'),
            (CHOICE_WINS, 'Winner only'),
            (CHOICE_LOSSES, 'Loser only'),
        ],
    )
    streak_min = _positive_integer_field(required=False, label='Minimum W/L Streak')


class SeasonFinderForm(BaseFinderForm):
    year_min = _start_year_field()
    year_max = _end_year_field()
    year_span = _positive_integer_field(
        required=False,
        label='Timespan (in Years)',
        help_text='Find results that span multiple seasons, e.g. \"3\" returns results such as \"2019-2021 Ed\".  Leaving blank is the same as entering 1.',  # noqa: E501
    )
    week_max = _positive_integer_field(
        required=False,
        label='Through Week',
        help_text='Find partial seasons, e.g. \"7\" returns results such as \"2018 Rob (through week 7)\".  Leaving blank will result in only full seasons being returned.',  # noqa: E501
    )
    teams = _teams_multiple_choice_field()
    wins_min = forms.IntegerField(required=False, label='Minimum Wins')
    wins_max = forms.IntegerField(required=False, label='Maximum Wins')
    expected_wins_min = forms.DecimalField(
        required=False,
        label='Minimum Expected Wins',
        decimal_places=3,
    )
    expected_wins_max = forms.DecimalField(
        required=False,
        label='Maximum Expected Wins',
        decimal_places=3,
    )
    points_min = forms.DecimalField(required=False, label='Minimum Points', decimal_places=2)
    points_max = forms.DecimalField(required=False, label='Maximum Points', decimal_places=2)
    avg_score_min = forms.DecimalField(required=False, label='Minimum Average Score', decimal_places=2)  # noqa: E501
    avg_score_max = forms.DecimalField(required=False, label='Maximum Average Score', decimal_places=2)  # noqa: E501
    place_min = _positive_integer_field(required=False, label='Minimum Place')
    place_max = _positive_integer_field(
        required=False,
        label='Maximum Place',
        help_text='Place filters will be ignored if \"Timespan (in Years)\" is greater than 1.',
    )
    playoffs = forms.TypedChoiceField(
        required=False,
        label='Finish',
        widget=forms.RadioSelect,
        choices=[
            ('', 'Any finish'),
            (CHOICE_MADE_PLAYOFFS, 'Made playoffs'),
            (CHOICE_MISSED_PLAYOFFS, 'Missed playoffs'),
        ],
    )
    clinched = forms.TypedChoiceField(
        required=False,
        label='Clinching Status (Through Chosen Week)',
        widget=forms.RadioSelect,
        choices=[
            ('', 'Any status'),
            (CHOICE_CLINCHED_PLAYOFFS, 'Clinched playoffs'),
            (CHOICE_CLINCHED_BYE, 'Clinched bye'),
            (CHOICE_ELIMINATED_EARLY, 'Eliminated early'),
        ],
    )
    bye = forms.BooleanField(required=False, label='Earned Bye')
    champion = forms.BooleanField(required=False, label='Won Sanderson Cup')


class TradeFinderForm(BaseFinderForm):
    year_min = _start_year_field()
    year_max = _end_year_field()
    week_min = _positive_integer_field(required=False, label='Start Week')
    week_max = _positive_integer_field(required=False, label='End Week')
    receivers = _teams_multiple_choice_field(label='Receiver')
    senders = _teams_multiple_choice_field('Sender')
    positions = _positions_multiple_choice_field()
    includes_draft_picks = forms.BooleanField(required=False, label='Includes Draft Picks')
    assets_display = forms.TypedChoiceField(
        required=False,
        label='Display Options',
        widget=forms.RadioSelect,
        choices=[
            ('', 'All assets in trades'),
            (CHOICE_MATCHING_ASSETS_ONLY, 'Matching assets only'),
        ],
    )
    player = forms.CharField(required=False, label='Player Name')

    filter_threshold = 1


class KeeperFinderForm(BaseFinderForm):
    year_min = _start_year_field()
    year_max = _end_year_field()
    round_min = _positive_integer_field(required=False, label='Earliest Round')
    round_max = _positive_integer_field(required=False, label='Latest Round')
    positions = _positions_multiple_choice_field()
    times_kept = forms.TypedMultipleChoiceField(
        required=False,
        label='Times Kept',
        widget=forms.CheckboxSelectMultiple,
        choices=[(1, 1), (2, 2)]
    )
    teams = _teams_multiple_choice_field()
    player = forms.CharField(required=False, label='Player Name')

    filter_threshold = 1


class DraftPickFinderForm(BaseFinderForm):
    year_min = _start_year_field()
    year_max = _end_year_field()
    round_min = _positive_integer_field(required=False, label='Earliest Round')
    round_max = _positive_integer_field(required=False, label='Latest Round')
    overall_pick_min = _positive_integer_field(required=False, label='Earliest Overall Pick')
    overall_pick_max = _positive_integer_field(required=False, label='Latest Overall Pick')
    positions = _positions_multiple_choice_field()
    teams = _teams_multiple_choice_field()
    keeper = _yes_no_field('Keeper')
    traded = forms.BooleanField(required=False, label='Traded')
    player = forms.CharField(required=False, label='Player Name')

    filter_threshold = 1
