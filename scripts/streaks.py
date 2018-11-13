from collections import defaultdict

from blingaleague.models import Member, TeamMultiSeasons


def points_streak(min_points, min_streak=6, include_playoffs=False):
    streaks = defaultdict(list)

    for team in Member.objects.all():
        streak = 0
        tms = TeamMultiSeasons(team.id, include_playoffs=include_playoffs)
        for i, gs in enumerate(tms.game_scores):
            if gs >= min_points:
                streak += 1
            else:
                if streak > 0:
                    streaks[streak].append((team, tms.games[i-1]))
                streak = 0
        if gs >= min_points:
            streaks[streak].append((team, tms.games[-1]))

    for s, l in sorted(streaks.items(), key=lambda x: x[0], reverse=True):
        if s < min_streak:
            continue

        print("# {} games".format(s))
        for t, g in l:
            print("{} (ended {})".format(t, g.week_object))
        print('')
