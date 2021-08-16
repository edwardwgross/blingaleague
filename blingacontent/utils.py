from httplib2 import Http

from pathlib import Path

from django.conf import settings

from googleapiclient.discovery import build

from oauth2client import file, client, tools

from blingaleague.models import Week, Season, TeamSeason, PLAYOFF_TEAMS, \
                                SEMIFINALS_TITLE_BASE, QUARTERFINALS_TITLE_BASE, \
                                BLINGABOWL_TITLE_BASE
from blingaleague.utils import regular_season_weeks, blingabowl_week


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
        flags = tools.argparser.parse_args(args=['--noauth_local_webserver'])
        creds = tools.run_flow(flow, store, flags=flags)
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

    if last_week.week <= regular_season_weeks(last_week.year):
        sections.append([
            "# [Standings]({})".format(
                current_season.gazette_link,
            ),
            current_season.gazette_str,
            '## Blingalytics Ratings',
            blingalytics_ratings_section(current_season),
        ])
    elif last_week.week == blingabowl_week(last_week.year):
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
    else:
        sections.append(postmortems_section(last_week, current_season))

    if last_week.week == blingabowl_week(last_week.year):
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


def postmortems_section(week_obj, season):
    postmortems_section = ['# Season Postmortems']

    dead_teams = []

    if week_obj.week == regular_season_weeks(week_obj.year):
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


def blingalytics_ratings_section(season):
    expected_wins_ranking = sorted(
        season.standings_table,
        key=lambda x: x.expected_win_pct,
        reverse=True,
    )

    ratings_rows = []
    for i, team_season in enumerate(expected_wins_ranking, 1):
        ratings_rows.append(
            "{}. {}, {:.0f}".format(
                i,
                team_season.team.nickname,
                1000 * team_season.expected_win_pct,
            ),
        )

    return '\n'.join(ratings_rows)
