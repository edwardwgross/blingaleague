import numpy
import random
import statistics

from collections import defaultdict

from blingaleague.models import TeamSeason, Game, Season


def two_stat_correl(attr1, attr2, min_year=None):
    list1 = []
    list2 = []
    for ts in TeamSeason.all():
        if ts.is_partial:
            continue
        if min_year is not None and ts.year < min_year:
            continue
        list1.append(float(getattr(ts, attr1)))
        list2.append(float(getattr(ts, attr2)))
    return numpy.corrcoef(list1, list2)[0][1]


def in_season_correl(attr1, attr2, cutoff_week):
    list_remain = []
    list_part = []
    for ts_full in TeamSeason.all():
        if ts_full.is_partial:
            continue
        ts_part = TeamSeason(ts_full.team.id, ts_full.year, week_max=cutoff_week)
        attr1_part = getattr(ts_part, attr1)
        attr2_remain = getattr(ts_full, attr2) - getattr(ts_part, attr2)
        list_part.append(float(attr1_part))
        list_remain.append(float(attr2_remain))
    return numpy.corrcoef(list_part, list_remain)[0][1]


def full_season_correl(year, attr1, attr2):
    standings = Season(year)
    list1 = [float(getattr(ts, attr1)) for ts in standings.table]
    list2 = [float(getattr(ts, attr2)) for ts in standings.table]
    return numpy.corrcoef(list1, list2)[0][1]


def one_stat_to_all(base_attr, min_year=None):
    correlations = defaultdict(list)

    for attribute in dir(TeamSeason):
        try:
            correl = two_stat_correl(attribute, base_attr, min_year=min_year)
            if -1 <= correl <= 1:
                # sometimes, 'nan' is returned, it's a number-y type
                # but we still want to ignore it
                correlations[correl].append(attribute)
        except Exception:
            # some attributes aren't numeric
            pass

    return correlations


def generate_score(low, high):
    rand = random.random()
    return low + ((high - low) * rand)


def generate_seasons(average_score, diff, limit=300):
    target = 13 * average_score

    low = average_score - diff
    high = average_score + diff

    seasons = []

    counted_runs = 0
    while counted_runs < limit:
        scores = []
        for _ in range(12):
            scores.append(generate_score(low, high))

        total_12 = sum(scores)
        remaining = target - total_12

        if not (low <= remaining <= high):
            continue

        scores.append(remaining)

        seasons.append(scores)

        counted_runs += 1

    return seasons


def distribution_correl(average_score):

    def _correl(average_score, diff):
        xw_list = []
        sd_list = []

        season_list = generate_seasons(average_score, diff)

        for season in season_list:
            xw = float(Game.expected_wins(*season))
            sd = statistics.pstdev(season)

            xw_list.append(xw)
            sd_list.append(sd)

        correl = numpy.corrcoef(xw_list, sd_list)[0][1]

        print("=== {} +/- {} ===".format(average_score, diff))
        print("Avg XW: {:.3f}".format(statistics.mean(xw_list)))
        print("Avg SD: {:.3f}".format(statistics.mean(sd_list)))
        print("Correl: {:.3f}".format(correl))
        print('')

    _correl(average_score, 50)
    _correl(average_score, 10)


def play_out_season(average_score):
    variable_seasons = generate_seasons(average_score, 50, limit=2000)
    consistent_seasons = generate_seasons(average_score, 10, limit=2000)

    variable_win_counts = []
    consistent_win_counts = []

    for i, variable_season in enumerate(variable_seasons):
        consistent_season = consistent_seasons[i]

        variable_win_count = 0
        consistent_win_count = 0

        for j, variable_score in enumerate(variable_season):
            consistent_score = consistent_season[j]

            if variable_score > consistent_score:
                variable_win_count += 1
            else:
                consistent_win_count += 1

        variable_win_counts.append(variable_win_count)
        consistent_win_counts.append(consistent_win_count)

    print("Avg wins for variable: {:.2f}".format(statistics.mean(variable_win_counts)))
    print("Avg wins for consistent: {:.2f}".format(statistics.mean(consistent_win_counts)))
