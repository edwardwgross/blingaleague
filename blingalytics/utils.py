from blingaleague.models import TeamSeason


MIN_GAMES_THRESHOLD = 6


def has_enough_games(team_season):
    return len(team_season.regular_season.games) >= MIN_GAMES_THRESHOLD


def sorted_seasons_by_stat(stat_function, limit=None, sort_desc=False):
    all_stats = {}
    for team_season in TeamSeason.all():
        if not has_enough_games(team_season):
            continue

        all_stats[team_season] = stat_function(team_season.game_scores)

    return build_ranked_seasons_table(
        all_stats,
        limit=limit,
        sort_desc=sort_desc,
    )


def sorted_seasons_by_attr(attr, limit=None, sort_desc=False):
    all_attrs = {}
    for team_season in TeamSeason.all():
        if not has_enough_games(team_season):
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
        if not has_enough_games(team_season):
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