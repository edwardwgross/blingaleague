import decimal

from django.contrib.humanize.templatetags.humanize import intcomma

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
        2: 60,
        3: 30,
        4: 20,
        5: 10,
        6: 10,
        total_teams - 3: -5,
        total_teams - 2: -5,
        total_teams - 1: -10,
        total_teams: -20,
    }

    final_place = team_season.playoff_finish_numeric or team_season.place_numeric

    points += place_to_points.get(team_season.place_numeric, 0)
    points += place_to_points.get(team_season.playoff_finish_numeric, 0)

    points += 2 * ((team_season.expected_wins * 10) - 65)

    return points / 4


def year_adjustment(team_season, base_year):
    if team_season.year > base_year:
        return 0

    year_diff = base_year - team_season.year

    if year_diff == 0:
        return 1

    recency_cutoff = 3

    if year_diff < recency_cutoff:
        return decimal.Decimal(0.5)

    return decimal.Decimal((recency_cutoff / year_diff) * 0.2)


def team_power_scores(team):
    years = [season.year for season in Season.all()]
    max_year = max(years)

    scores = []
    for year in sorted(years):
        team_season = TeamSeason(team.id, year)
        points = power_points(team_season)
        scores.append(year_adjustment(team_season, max_year) * points)

    return scores


def gazette_output():
    team_scores = {}
    for team in Member.objects.filter(defunct=False):
        team_scores[team] = team_power_scores(team)

    lines = []
    total_teams = len(team_scores)
    for i, (team, power_scores) in enumerate(sorted(team_scores.items(), key=lambda x: sum(x[1]))):
        print("{}. {}: {:.0f} - {}".format(
            total_teams - i,
            team.nickname,
            sum(power_scores),
            ' / '.join(map(lambda x: "{:.1f}".format(x), power_scores)),
            ))

        last_season = TeamSeason(team.id, Season.latest().year)
        last_3_seasons = team.last_x_seasons(3)
        all_seasons = team.seasons

        lines.append("### {}. [{}]({}) (last year: XXX)".format(
            total_teams - i,
            team,
            team.gazette_link,
        ))
        lines.append('')

        lines.append("- [{}]({}): {}".format(
            last_season.year,
            last_season.gazette_link,
            team_seasons_output(last_season),
        ))
        lines.append("- Last 3 seasons: {}".format(team_seasons_output(last_3_seasons)))
        lines.append("- All-time: {}".format(team_seasons_output(all_seasons)))
        lines.append('')

        lines.append('XXX XXX XXX XXX XXX XXX')
        lines.append('')

        lines.append('NFL equivalent: **XXX**')
        lines.append('')
        lines.append('')

    return lines


def team_seasons_output(team_seasons_obj):
    parts = [
        team_seasons_obj.record,
        "{} points".format(intcomma(team_seasons_obj.points)),
        "{:.2f} expected wins".format(team_seasons_obj.expected_wins),
    ]

    if team_seasons_obj.is_single_season:
        parts.append("{} place".format(team_seasons_obj.place))
    else:
        parts.append("average place: {:.1f}".format(team_seasons_obj.average_place))
        if team_seasons_obj.playoff_appearances > 0:
            parts.append("playoff appearances: {}".format(team_seasons_obj.playoff_appearances))
        if team_seasons_obj.blingabowl_appearances > 0:
            parts.append("Blingabowl appearances: {}".format(team_seasons_obj.blingabowl_appearances))
        if team_seasons_obj.championships > 0:
            parts.append("Sanderson Cup wins: {}".format(team_seasons_obj.championships))

    return ', '.join(parts)
