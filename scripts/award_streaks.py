from collections import defaultdict

from blingaleague.models import *


def streaks_without_winning(award):
    streaks = defaultdict(list)

    for team in TeamMultiSeasons.all():
        last_award = None

        if award == 'blangums':
            award_games = team.blangums_games
        elif award == 'slapped heartbeat':
            award_games = team.slapped_heartbeat_games
        else:
            raise ValueError("Award argument must be 'blangums' or 'slapped heartbeat'")

        for award_game in award_games:
            if last_award is None:
                gap = award_game.week_object - team.games[0].week_object
            else:
                gap = award_game.week_object - last_award - 1

            streaks[gap].append((team.team, last_award, award_game.week_object))
            last_award = award_game.week_object

        if last_award is not None:
            cur_gap = team.games[-1].week_object - last_award
            streaks[cur_gap].append((team.team, last_award, None))

    return streaks


def print_streaks(streak_dict, min_streak):
    for week_count, team_list in sorted(streak_dict.items(), reverse=True):
        if week_count < min_streak:
            break

        print("{} weeks".format(week_count))

        for team, start_week, end_week in team_list:
            if start_week is None:
                start_week = 'inception'
            else:
                start_week = str(start_week.next).lower()

            if end_week is None:
                end_week = 'current'
            else:
                end_week = str(end_week.previous).lower()

            print("- {}, {} through {}".format(team, start_week, end_week))
