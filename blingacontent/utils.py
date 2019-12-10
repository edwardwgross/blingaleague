from httplib2 import Http

from pathlib import Path

from django.conf import settings
from django.core import urlresolvers

from googleapiclient.discovery import build

from oauth2client import file, client, tools

from blingaleague.models import Week, Season, TeamSeason, \
                                EXPANSION_SEASON, REGULAR_SEASON_WEEKS, BLINGABOWL_WEEK, \
                                OUTCOME_WIN, OUTCOME_LOSS, OUTCOME_ANY, PLAYOFF_TEAMS, \
                                SEMIFINALS_TITLE_BASE, QUARTERFINALS_TITLE_BASE, \
                                BLINGABOWL_TITLE_BASE

from blingalytics.utils import get_playoff_odds


SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send',
]


def get_gmail_service():
    token_path = Path(settings.BASE_DIR) / 'data' / 'gmail_token.json'
    store = file.Storage(token_path)
    creds = store.get()
    if not creds or creds.invalid:
        credentials_path = Path(settings.BASE_DIR) / 'data' / 'gmail_credentials.json'
        flow = client.flow_from_clientsecrets(credentials_path, SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('gmail', 'v1', http=creds.authorize(Http()))
    return service


def new_gazette_body_template():
    last_week = Week.latest()

    current_season = Season.latest(week_max=last_week.week)

    sections = []

    sections.append([
        "# [{}]({}) Recap".format(
            Week.week_to_title(last_week.year, last_week.week),
            last_week.gazette_link,
        ),
        last_week.gazette_str,
    ])

    if last_week.week <= REGULAR_SEASON_WEEKS:
        sections.append([
            "# [Standings]({})".format(
                current_season.gazette_link,
            ),
            current_season.gazette_str,
        ])
    elif last_week.week == BLINGABOWL_WEEK:
        sections.append([
            "# [Final Standings]({})".format(
                current_season.gazette_link,
            ),
        ])
        sections.append(['# Final Payouts']),

    sections.append([
        '# Weekly Awards',
        '### Team Blangums:',
        '### Slapped Heartbeat:',
        '### Weekly MVP:',
        '### Dud of the Week:',
        '### Start of the Week:',
        '### Misplay of the Week:',
        '### Pickup of the Week:',
        '### Blessed Cahoots:',
        '### Pryor Play of the Week:',
    ])

    if current_season.is_partial:
        if last_week.week >= 8:
            sections.append([
                '# Playoff Scenarios',
            ])

        if last_week.week <= 10:
            sections.append(playoff_odds_section(last_week))
    else:
        sections.append(postmortems_section(last_week, current_season))

    if last_week.week == BLINGABOWL_WEEK:
        sections.append(['# Blingapower Rankings'])
        sections.append(['# Draft Lottery'])
    else:
        sections.append([
            "# {} Preview".format(
                Week.week_to_title(last_week.year, last_week.week + 1),
            ),
            '## Game of the Blingaweek',
            '## Other Blingamatches',
        ])

    sections.append([
        '# Closing Thoughts',
    ])

    return '\n\n\n'.join(
        ['\n\n'.join(section) for section in sections],
    )


def playoff_odds_section(week_obj):
    playoff_odds_section = [
        '# Playoff Odds',
        'Since expansion, this is how often teams with each record have made the playoffs:',
    ]

    current_odds = get_playoff_odds(week_obj.week)

    if week_obj.week < REGULAR_SEASON_WEEKS:
        next_week_odds = get_playoff_odds(week_obj.week + 1)
    else:
        next_week_odds = current_odds

    for win_count, odds in sorted(current_odds.items()):
        loss_count = week_obj.week - win_count

        season_finder_url = urlresolvers.reverse_lazy('blingalytics.season_finder')
        querystring = "?year_min={}&year_max={}&week_max={}&wins_min={}&wins_max={}".format(
            EXPANSION_SEASON,
            week_obj.year - 1,
            week_obj.week,
            win_count,
            win_count,
        )
        season_finder_link = "{}{}{}".format(
            settings.FULL_SITE_URL,
            season_finder_url,
            querystring,
        )

        with_win = next_week_odds[win_count + 1][OUTCOME_WIN]['pct']
        with_loss = next_week_odds[win_count][OUTCOME_LOSS]['pct']

        playoff_odds_section.append(
            "- [{}-{}]({}): {:.0f}% ({:.0f}% with week {} win, {:.0f}% with loss)".format(
                win_count,
                loss_count,
                season_finder_link,
                100 * odds[OUTCOME_ANY]['pct'],
                100 * with_win,
                week_obj.week + 1,
                100 * with_loss,
            ),
        )

    return playoff_odds_section


def postmortems_section(week_obj, season):
    postmortems_section = ['# Season Postmortems']

    dead_teams = []

    if week_obj.week == REGULAR_SEASON_WEEKS:
        dead_teams = season.standings_table[PLAYOFF_TEAMS:]
    else:
        for game in week_obj.games:
            if game.playoff_title_base in (QUARTERFINALS_TITLE_BASE, SEMIFINALS_TITLE_BASE):
                dead_teams.append(TeamSeason(game.loser.id, week_obj.year))

            if game.playoff_title_base == BLINGABOWL_TITLE_BASE:
                dead_teams.extend(map(
                    lambda x: TeamSeason(x.id, week_obj.year),
                    [game.winner, game.loser],
                ))

    dead_teams = sorted(
        dead_teams,
        key=lambda x: (x.playoff_finish_numeric, x.place_numeric),
        reverse=True,
    )

    for team_season in dead_teams:
        postmortems_section.append(team_season.gazette_postmortem_str)

    return postmortems_section
