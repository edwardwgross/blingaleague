import base64

from email.mime.text import MIMEText

from httplib2 import Http

from django.conf import settings
from django.core.cache import caches

from googleapiclient.discovery import build

from oauth2client import file, client, tools

from blingaleague.models import Week, Season, TeamSeason, PLAYOFF_TEAMS, \
                                Member, FakeMember, Player, \
                                SEMIFINALS_TITLE_BASE, QUARTERFINALS_TITLE_BASE, \
                                BLINGABOWL_TITLE_BASE
from blingaleague.utils import regular_season_weeks, blingabowl_week, semifinals_week


CACHE = caches['blingaleague']

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send',
]


def get_gmail_service():
    token_path = settings.DATA_DIR / 'gmail_token.json'
    store = file.Storage(token_path)
    creds = store.get()
    if not creds or creds.invalid:
        credentials_path = settings.DATA_DIR / 'gmail_credentials.json'
        flow = client.flow_from_clientsecrets(credentials_path, SCOPES)
        flags = tools.argparser.parse_args(args=['--noauth_local_webserver'])
        creds = tools.run_flow(flow, store, flags=flags)
    service = build('gmail', 'v1', http=creds.authorize(Http()))
    return service


def send_gazette_to_members(gazette):
    gmail_service = get_gmail_service()

    recipients = []
    for member in Member.objects.filter(defunct=False):
        recipients.append("{} {} <{}>".format(
            member.first_name,
            member.last_name,
            member.email,
        ))

    for fake_member in FakeMember.objects.filter(active=True):
        recipients.append("{} <{}>".format(
            fake_member.name,
            fake_member.email,
        ))

    message = MIMEText(gazette.to_email(include_css=True), 'html')
    message['to'] = ', '.join(sorted(recipients))
    message['from'] = 'Blingaleague Commissioner <blingaleaguecommissioner@gmail.com>'
    message['subject'] = "The Sanderson Gazette - {}".format(gazette)

    message64 = base64.urlsafe_b64encode(message.as_string().encode())

    gmail_service.users().messages().send(
        userId='me',
        body={
            'raw': message64.decode(),
        },
    ).execute()


def new_gazette_body_template():
    last_week = Week.latest()
    current_week = last_week.next

    current_season = Season.latest()

    sections = []

    sections.append([
        "# [{}]({}) Recap".format(
            Week.week_to_title(last_week.year, last_week.week),
            last_week.gazette_link,
        ),
        last_week.gazette_str,
    ])
    if last_week.trades:
        sections.append([
            '## Trades',
            '\n\n'.join([trade.gazette_str for trade in last_week.trades]),
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
        '### Team Blangums',
        '### Slapped Heartbeat',
        '### Weekly MVP',
        '### Dud of the Week',
        '### Start of the Week',
        '### Misplay of the Week',
        '### Pickup of the Week',
        '### Blessed Cahoots',
        '### Pryor Play of the Week',
        '### D\'Ernest D\'oh',
    ])

    if current_season.is_partial:
        if last_week.week >= (regular_season_weeks(last_week.year) - 5):
            sections.append([
                '# Playoff Scenarios',
            ])
    else:
        sections.append(postmortems_section(last_week, current_season))

    if last_week.week == blingabowl_week(last_week.year) and last_week.year == current_season.year:
        sections.append(['# Blingapower Rankings'])
        sections.append(['# Draft Lottery'])
    else:
        if last_week.week == semifinals_week(last_week.year) and current_season.trades:
            sections.append(year_in_trades_section(current_season))

        sections.append([
            "# {} Preview".format(
                Week.week_to_title(current_week.year, current_week.week),
            ),
            '## Game of the Blingaweek',
            '## Other Blingamatches',
            current_week.gazette_str,
        ])

    sections.append([
        '# Closing Thoughts',
    ])

    return '\n\n\n'.join(
        ['\n\n'.join(section) for section in sections],
    )


def postmortems_section(week_obj, season):
    postmortems_lines = ['# Season Postmortems']

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
        postmortems_lines.append(team_season.gazette_postmortem_str)

    return postmortems_lines


def year_in_trades_section(season):
    if not season.trades:
        return []

    year_in_trades_lines = ['# The Year in Trades']

    last_printed_week = None

    for trade in season.trades:
        if trade.week != last_printed_week:
            year_in_trades_lines.append("## [{}]({})".format(
                Week.week_to_title(trade.year, trade.week),
                trade.week_object.gazette_link,
            ))
            last_printed_week = trade.week

        year_in_trades_lines.append(trade.gazette_str)

    return year_in_trades_lines


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


def print_current_playoff_odds(season=None):
    if season is None:
        season = Season.latest()

    odds = season.playoff_odds()

    for type in ('playoffs', 'bye'):
        print(type.upper())
        for team, team_odds in sorted(odds.items(), key=lambda x: x[1][type], reverse=True):
            print("{:.0%}: {}".format(team_odds[type], team))
        print('')


def build_player_link(raw_name):
    allowed_special_chars = ' -.,\'()'
    lead_chars = ''
    trail_chars = ''
    clean_name = ''

    for letter in raw_name:
        if not (letter.isalnum() or letter in allowed_special_chars):
            return None

        if len(clean_name) >= 1 or letter.isalnum():
            clean_name += letter
        else:
            lead_chars += letter

    raw_name = clean_name
    clean_name = ''
    for letter in raw_name[::-1]:
        if len(clean_name) >= 1 or letter.isalnum():
            clean_name = letter + clean_name
        elif letter == '.' and raw_name[-3:] in ('Jr.', 'Sr.'):
            clean_name = letter + clean_name
        else:
            trail_chars = letter + trail_chars

    if clean_name.endswith('\'s'):
        clean_name = clean_name[:-2]
        trail_chars = '\'s' + trail_chars

    if len(clean_name) >= 1:
        # key caching has length limit, so do *something* to prevent that
        name_max_len = 100
        player_obj = Player(clean_name[:name_max_len])
        if player_obj.has_data:
            return "{}[{}]({}){}".format(
                lead_chars,
                clean_name,
                player_obj.gazette_link,
                trail_chars,
            )

    return None


def add_player_links_to_text(gazette):
    cached_body = CACHE.get(gazette.body_cache_key)
    if cached_body:
        return cached_body

    newline_char = '\r\n'
    old_lines = gazette.body.split(newline_char)
    new_lines = []

    for line in old_lines:
        old_words = line.strip().split(' ')
        new_words = []
        index = 0
        while index < len(old_words):
            offset = 0

            name_1 = old_words[index]

            try:
                name_2 = "{} {}".format(name_1, old_words[index + 1])
            except IndexError:
                name_2 = old_words[index]

            try:
                name_3 = "{} {}".format(name_2, old_words[index + 2])
            except IndexError:
                name_3 = name_2

            player_1_link = build_player_link(name_1)
            player_2_link = build_player_link(name_2)
            player_3_link = build_player_link(name_3)

            # test longest name first, in case in contains a shorter one
            if player_3_link:
                new_word = player_3_link
                offset = 2
            elif player_2_link:
                new_word = player_2_link
                offset = 1
            elif player_1_link:
                new_word = player_1_link
                offset = 0
            else:
                new_word = name_1
                offset = 0

            new_words.append(new_word)
            index = index + 1 + offset

        new_lines.append(' '.join(new_words))

    new_body = newline_char.join(new_lines)

    CACHE.set(gazette.body_cache_key, new_body)

    return new_body
