import numpy
import random
import statistics

from blingaleague.models import TeamSeason, Game


def two_stat_correl(attr1, attr2):
    list1 = []
    list2 = []
    for ts in TeamSeason.all():
        if ts.is_partial:
            continue
        list1.append(float(getattr(ts, attr1)))
        list2.append(float(getattr(ts, attr2)))
    return numpy.corrcoef(list1, list2)[0][1]


def in_season_correl(attr, week):
    list_remain = []
    list_part = []
    for ts_full in TeamSeason.all():
        if ts_full.is_partial:
            continue
        ts_part = TeamSeason(ts_full.team.id, ts_full.year, week_max=week)
        attr_part = getattr(ts_part, attr)
        wins_remain = ts_full.win_count - ts_part.win_count
        list_part.append(float(attr_part))
        list_remain.append(float(wins_remain))
    return numpy.corrcoef(list_part, list_remain)[0][1]


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
