import statistics

from django.core.cache import caches

from blingaleague.models import TeamSeason, Week, Season, \
                                REGULAR_SEASON_WEEKS, \
                                EXPANSION_SEASON, \
                                OUTCOME_WIN, OUTCOME_LOSS, OUTCOME_ANY


CACHE = caches['blingaleague']

MIN_GAMES_THRESHOLD = 6


def has_enough_games(team_season):
    return len(team_season.regular_season.games) >= MIN_GAMES_THRESHOLD


def sorted_seasons_by_attr(
    attr,
    limit=None,
    sort_desc=False,
    min_games=1,
    display_attr=None,
):
    all_attrs = []
    for team_season in TeamSeason.all():
        if len(team_season.games) < min_games:
            continue

        all_attrs.append((team_season, getattr(team_season, attr)))

    return build_ranked_seasons_table(
        all_attrs,
        limit=limit,
        sort_desc=sort_desc,
        display_attr=display_attr,
    )


def sorted_expected_wins_odds(win_count, limit=None, sort_desc=False):
    all_odds = []
    for team_season in TeamSeason.all():
        if team_season.is_partial:
            continue

        win_odds = team_season.expected_win_distribution.get(win_count, 0)
        if win_odds > 0:
            # we'll format as a percent, so multiply here
            all_odds.append((team_season, 100 * win_odds))

    return build_ranked_seasons_table(
        all_odds,
        limit=limit,
        sort_desc=sort_desc,
        num_format='{:.2f}%'
    )


def build_ranked_seasons_table(
    season_stat_tuples,
    limit=None,
    sort_desc=False,
    num_format='{:.2f}',
    display_attr=None,
):
    sorted_seasons = sorted(
        season_stat_tuples,
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

        if display_attr is not None:
            display_value = getattr(team_season, display_attr)
        else:
            if type(stat_value) == int:
               num_format = '{:.0f}'
            display_value = num_format.format(stat_value)

        season_dict = {
            'rank': rank,
            'team_season': team_season,
            'value': display_value,
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
    cache_key = "blingalytics_playoff_odds|{}|{}".format(
        week,
        min_year,
    )

    if cache_key in CACHE:
        return CACHE.get(cache_key)

    week = min(week, REGULAR_SEASON_WEEKS)

    # don't use defaultdict, because we can't pickle it for caching
    playoff_odds = {}
    win_count = 0
    while win_count <= week:
        playoff_odds[win_count] = {}

        for outcome in (OUTCOME_ANY, OUTCOME_WIN, OUTCOME_LOSS):
            playoff_odds[win_count][outcome] = {
                'total': 0,
                'playoffs': 0,
            }

        win_count += 1

    for season in Season.all(week_max=week):
        if season.year < min_year:
            continue

        if season.regular_season.is_partial:
            continue

        for ts in season.standings_table:
            outcomes = (OUTCOME_ANY, ts.week_outcome(week))

            for outcome in outcomes:
                playoff_odds[ts.win_count][outcome]['total'] += 1

                playoffs = ts.regular_season.made_playoffs
                if playoffs:
                    playoff_odds[ts.win_count][outcome]['playoffs'] += 1

    for outcome in (OUTCOME_ANY, OUTCOME_WIN, OUTCOME_LOSS):
        win_count = 0

        max_wins = week
        if outcome == OUTCOME_LOSS:
            max_wins = week - 1

        while win_count <= max_wins:
            playoffs = playoff_odds[win_count][outcome]['playoffs']
            total = playoff_odds[win_count][outcome]['total']

            if total > 0:
                pct = playoffs / total
            else:
                # use whatever we were at last week as the default if we don't
                # have any history for this week/win_count/outcome combo
                if week > 1:
                    last_week_odds = get_playoff_odds(week - 1, min_year=min_year)

                    if outcome == OUTCOME_WIN:
                        pct = last_week_odds[max(0, win_count - 1)][OUTCOME_ANY]['pct']
                    elif outcome == OUTCOME_LOSS:
                        pct = last_week_odds[win_count][OUTCOME_ANY]['pct']
                    else:
                        pct = statistics.mean([
                            last_week_odds[max(0, win_count - 1)][OUTCOME_ANY]['pct'],
                            last_week_odds[min(week - 1, win_count)][OUTCOME_ANY]['pct'],
                        ])
                else:
                    pct = 0

            playoff_odds[win_count][outcome]['pct'] = pct

            win_count += 1

    CACHE.set(cache_key, playoff_odds)

    return playoff_odds
