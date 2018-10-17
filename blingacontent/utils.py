from httplib2 import Http

from pathlib import Path

from django.conf import settings
from django.core import urlresolvers

from googleapiclient.discovery import build

from oauth2client import file, client, tools

from blingaleague.models import Week, Standings, EXPANSION_SEASON, REGULAR_SEASON_WEEKS

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

    current_standings = Standings.latest()

    sections = []

    sections.append([
        "# [Week {}]({}) Recap".format(
            last_week.week,
            last_week.gazette_link,
        ),
        last_week.gazette_str,
    ])

    sections.append([
        "# [Standings]({})".format(
            current_standings.gazette_link,
        ),
        current_standings.gazette_str,
    ])

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

    if current_standings.is_partial:
        sections.append(playoff_odds_section(last_week))

    sections.append([
        "# Week {} Preview".format(
            last_week.week + 1,
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

        with_win = next_week_odds[win_count + 1]
        with_loss = next_week_odds[win_count]

        playoff_odds_section.append(
            "- [{}-{}]({}): {:.0f}% ({:.0f}% with win, {:.0f}% with loss)".format(
                win_count,
                loss_count,
                season_finder_link,
                100 * odds['pct'],
                100 * next_week_odds[win_count + 1]['pct'],
                100 * next_week_odds[win_count]['pct'],
            ),
        )

    return playoff_odds_section
