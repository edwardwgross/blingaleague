from django import forms

from blingaleague.models import Member


CHOICE_BLANGUMS = 'team_blangums'
CHOICE_SLAPPED_HEARTBEAT = 'slapped_heartbeat'
CHOICE_WINS = 'wins'
CHOICE_LOSSES = 'losses'
CHOICE_REGULAR_SEASON = 'regular'
CHOICE_PLAYOFFS = 'playoffs'
CHOICE_MADE_PLAYOFFS = 'made_playoffs'
CHOICE_MISSED_PLAYOFFS = 'missed_playoffs'


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
                "You must filter on at least {} fields to see results".format(
                    self.filter_threshold,
                ),
            )
            return False

        return True


class GameFinderForm(BaseFinderForm):
    year_min = forms.IntegerField(required=False, label='Start Year')
    year_max = forms.IntegerField(required=False, label='End Year')
    week_min = forms.IntegerField(required=False, label='Start Week')
    week_max = forms.IntegerField(required=False, label='End Week')
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
    teams = forms.TypedMultipleChoiceField(
        required=False,
        label='Teams',
        widget=forms.CheckboxSelectMultiple,
        choices=[
            (m.id, m.full_name) for m in Member.objects.all().order_by('first_name', 'last_name')
        ],
        coerce=int,
    )
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


class SeasonFinderForm(BaseFinderForm):
    year_min = forms.IntegerField(required=False, label='Start Year')
    year_max = forms.IntegerField(required=False, label='End Year')
    week_max = forms.IntegerField(required=False, label='Through Week')
    teams = forms.TypedMultipleChoiceField(
        required=False,
        label='Teams',
        widget=forms.CheckboxSelectMultiple,
        choices=[
            (m.id, m.full_name) for m in Member.objects.all().order_by('first_name', 'last_name')
        ],
        coerce=int,
    )
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
    bye = forms.BooleanField(required=False, label='Earned Bye')
    champion = forms.BooleanField(required=False, label='Won Sanderson Cup')
