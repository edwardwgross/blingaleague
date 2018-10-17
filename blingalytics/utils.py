from collections import defaultdict

from blingaleague.models import TeamSeason, Week, Year, \
                                Standings, REGULAR_SEASON_WEEKS, \
                                EXPANSION_SEASON


MIN_GAMES_THRESHOLD = 6


def has_enough_games(team_season):
    return len(team_season.regular_season.games) >= MIN_GAMES_THRESHOLD


def sorted_seasons_by_attr(attr, limit=None, sort_desc=False, min_games=1):
    all_attrs = {}
    for team_season in TeamSeason.all():
        if len(team_season.games) < min_games:
            continue

        all_attrs[team_season] = getattr(team_season, attr)

    return build_ranked_seasons_table(
        all_attrs,
        limit=limit,
        sort_desc=sort_desc,
    )


def sorted_expected_wins_odds(win_count, limit=None, sort_desc=False):
    all_odds = {}
    for team_season in TeamSeason.all():
        if team_season.is_partial:
            continue

        win_odds = team_season.expected_win_distribution.get(win_count, 0)
        if win_odds > 0:
            # we'll format as a percent, so multiply here
            all_odds[team_season] = 100 * win_odds

    return build_ranked_seasons_table(
        all_odds,
        limit=limit,
        sort_desc=sort_desc,
        num_format='{:.2f}%'
    )


def build_ranked_seasons_table(
    seasons_stats,
    limit=None,
    sort_desc=False,
    num_format='{:.2f}',
):
    sorted_seasons = sorted(
        seasons_stats.items(),
        key=lambda x: (x[1], x[0].year, x[0].team.nickname),
        reverse=sort_desc,
    )

    seasons_list = []
    last_value = None
    rank = 1
    for team_season, stat_value in sorted_seasons:
        if last_value is None or stat_value != last_value:
            # not a tie, so we need to increase the rank value
            rank = len(seasons_list) + 1

        if limit is not None and rank > limit:
            break

        print((team_season, stat_value, type(stat_value)))
        if type(stat_value) == int:
            num_format = '{:.0f}'

        season_dict = {
            'rank': rank,
            'team_season': team_season,
            'value': num_format.format(stat_value),
        }

        seasons_list.append(season_dict)

        last_value = stat_value

    return seasons_list


def build_belt_holder_list():
    holder = None
    starting_game = None
    defense_count = 0

    sequence = []

    for week in Week.all():
        if holder is None:
            holder = week.blangums

        for game in week.games:
            if game.loser == holder:
                sequence.append({
                    'holder': holder,
                    'starting_game': starting_game,
                    'defense_count': defense_count,
                })

                holder = game.winner
                starting_game = game
                defense_count = 0

                break
            elif game.winner == holder:
                if starting_game is None:
                    # it's the very first one
                    starting_game = game
                else:
                    defense_count += 1

                break

    sequence.append({
        'holder': holder,
        'starting_game': starting_game,
        'defense_count': defense_count,
    })

    return sequence


def get_playoff_odds(week, min_year=EXPANSION_SEASON):
    week = min(week, REGULAR_SEASON_WEEKS)

    playoff_odds = defaultdict(lambda: defaultdict(float))

    for year in Year.all():
        if year < min_year:
            continue

        standings = Standings(year, week_max=week)

        if standings.end_of_season_standings.is_partial:
            continue

        for ts in standings.table:
            playoff_odds[ts.win_count]['total'] += 1

            playoffs = ts.regular_season.playoffs
            if playoffs:
                playoff_odds[ts.win_count]['playoffs'] += 1

    previous_pct = 0.0
    win_count = 1
    while win_count <= week:
        playoffs = playoff_odds[win_count]['playoffs']
        total = playoff_odds[win_count]['total']

        pct = previous_pct
        if total > 0:
            pct = playoffs / total

        playoff_odds[win_count]['pct'] = pct

        previous_pct = pct
        win_count += 1

    return playoff_odds
