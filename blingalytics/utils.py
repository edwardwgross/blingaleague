import logging
import threading
import time

from django.core.cache import caches

from blingaleague.models import TeamSeason, Week, Season
from blingaleague.utils import regular_season_weeks


CACHE = caches['blingaleague']

PLAYOFF_ODDS_QUEUE_CACHE_KEY = 'blingaleague_playoff_odds_queue'
PLAYOFF_ODDS_ACTIVELY_RUNNING_CACHE_KEY = 'blingaleague_playoff_odds_actively_running'

TOP_SEASONS_DEFAULT_NUM_FORMAT = '{:.2f}'


def sorted_seasons_by_attr(
    attr,
    limit=None,
    sort_desc=False,
    require_full_season=False,
    min_games=1,
    display_attr=None,
    num_format=TOP_SEASONS_DEFAULT_NUM_FORMAT,
    week_max=None,
):
    all_attrs = []
    for team_season in TeamSeason.all():
        if week_max and (week_max < regular_season_weeks(team_season.year)):
            # ignore any specified week_max parameters that are longer than the season
            team_season = TeamSeason(team_season.team.id, team_season.year, week_max=week_max)
            if len(team_season.games) < week_max:
                continue
        else:
            if team_season.is_partial:
                if require_full_season or len(team_season.games) < min_games:
                    continue

        attr_value = getattr(team_season, attr)
        if attr_value is not None:
            all_attrs.append((team_season, getattr(team_season, attr)))

    return build_ranked_seasons_table(
        all_attrs,
        limit=limit,
        sort_desc=sort_desc,
        display_attr=display_attr,
        num_format=num_format,
    )


def build_ranked_seasons_table(
    season_stat_tuples,
    limit=None,
    sort_desc=False,
    num_format=TOP_SEASONS_DEFAULT_NUM_FORMAT,
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

    for week in sorted(Week.all()):
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


def run_playoff_odds_in_background(season):
    logger = logging.getLogger('blingaleague')
    logger.info("[{}] Requested playoff odds".format(season.playoff_odds_cache_key))

    current_queue = CACHE.get(PLAYOFF_ODDS_QUEUE_CACHE_KEY, [])
    if season.playoff_odds_cache_key not in current_queue:
        # if it is queued up, just wait for it and do nothing
        current_queue.append(season.playoff_odds_cache_key)
        CACHE.set(PLAYOFF_ODDS_QUEUE_CACHE_KEY, current_queue)
        logger.info("[{}] Added to playoff odds queue".format(season.playoff_odds_cache_key))

    if not CACHE.get(PLAYOFF_ODDS_ACTIVELY_RUNNING_CACHE_KEY):
        thread = threading.Thread(target=_run_next_queued_playoff_odds, daemon=True)
        thread.start()


def _run_next_queued_playoff_odds():
    logger = logging.getLogger('blingaleague')

    current_queue = CACHE.get(PLAYOFF_ODDS_QUEUE_CACHE_KEY, [])
    if not current_queue:
        return

    season_key = current_queue[0]

    logger.info("[{}] Running playoff odds".format(season_key))
    CACHE.set(PLAYOFF_ODDS_ACTIVELY_RUNNING_CACHE_KEY, season_key)
    CACHE.set(PLAYOFF_ODDS_QUEUE_CACHE_KEY, current_queue[1:])

    season = Season.playoff_odds_cache_key_to_season_object(season_key)

    t0 = time.time()
    _odds = season.playoff_odds()  # noqa: F841
    logger.info("[{}] Playoff odds finished after {:.1f} seconds".format(
        season_key,
        time.time() - t0,
    ))

    CACHE.delete(PLAYOFF_ODDS_ACTIVELY_RUNNING_CACHE_KEY)

    new_queue = CACHE.get(PLAYOFF_ODDS_QUEUE_CACHE_KEY, [])
    if new_queue:
        _run_next_queued_playoff_odds()
