import decimal

from blingaleague.models import *


def power_points(team_season):
    if len(team_season.games) == 0:
        return 0

    points = 0

    total_teams = 14
    if team_season.year < EXPANSION_SEASON:
        total_teams = 12

    place_to_points = {
        1: 100,
        2: 50,
        3: 25,
        4: 15,
        5: 5,
        6: 5,
        total_teams - 3: -5,
        total_teams - 2: -5,
        total_teams - 1: -10,
        total_teams: -20,
    }

    final_place = team_season.playoff_finish_numeric or team_season.place_numeric

    points += place_to_points.get(
        final_place,
        0,
    )

    points += (team_season.expected_wins * 10) - 65

    return points


def year_adjustment(team_season, base_year):
    if team_season.year > base_year:
        return 0

    year_diff = base_year - team_season.year

    if year_diff >= 5:
        return decimal.Decimal('0.1')

    return 1 - (decimal.Decimal('0.2') * year_diff)


raw_by_team = {}
adj_by_team = {}

years = range(2008, 2020)

for team in Member.objects.filter(defunct=False):
    raw_by_team[team] = []
    adj_by_team[team] = []
    for year in years:
        team_season = TeamSeason(team.id, year)
        points = power_points(team_season)
        raw_by_team[team].append(round(points))
        adj_by_team[team].append(round(year_adjustment(team_season, 2019) * points))

for by_team_dict in (raw_by_team, adj_by_team):
    print('')
    for i, (team, points_list) in enumerate(sorted(by_team_dict.items(), key=lambda x: sum(x[1]), reverse=True), 1):
        print("{}. {}: {} - {}".format(
            i,
            team.nickname,
            sum(points_list),
            ' / '.join(map(str, points_list)),
        ))
    print('')
