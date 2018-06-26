from blingaleague.models import TeamSeason


def team_season_game_stat(team_season, stat_function):
    return stat_function(team_season.game_scores)


def top_seasons_by_stat(stat_function, limit=None, sort_desc=False):
    all_stats = {}
    for team_season in TeamSeason.all():
        all_stats[team_season] = team_season_game_stat(
            team_season,
            stat_function,
        )

    sorted_seasons = sorted(
        all_stats.items(),
        key=lambda x: x[1],
        reverse=sort_desc,
    )

    return build_ranked_seasons_table(sorted_seasons, limit=limit)


def build_ranked_seasons_table(sorted_seasons, limit=None):
    seasons_list = []
    last_value = None
    rank = 1
    for team_season, stat_value in sorted_seasons:
        if last_value is None or stat_value != last_value:
            # not a tie, so we need to increase the rank value
            rank = len(seasons_list) + 1

        if limit is not None and rank > limit:
            break

        season_dict = {
            'rank': rank,
            'team_season': team_season,
            'value': stat_value,
        }

        seasons_list.append(season_dict)

        last_value = stat_value

    return seasons_list
