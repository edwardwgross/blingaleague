from collections import defaultdict

from blingaleague.models import Standings, Year


outcomes = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

for year in Year.all()[:-1]:
    week = 1
    while week <= 13:
        standings = Standings(year, week_max=week)
        for ts in standings.table:
            playoffs = ts.regular_season.playoffs
            outcomes[week][ts.win_count]['total'] += 1
            if playoffs:
                outcomes[week][ts.win_count]['playoffs'] += 1
        week += 1

for week, week_outcomes in sorted(outcomes.items()):
    for win, results in sorted(week_outcomes.items()):
        pct = results['playoffs'] / results['total']
        outcomes[week][win]['pct'] = pct

print('Record,Playoff Pct,Change with Loss,Change with Win')
for week, week_outcomes in sorted(outcomes.items()):
    #print('')
    #print('Record,Playoff Pct,Change with Loss,Change with Win')
    for win, results in sorted(week_outcomes.items()):
        wd = outcomes[week+1][win+1]['pct']
        ld = outcomes[week+1][win]['pct']
        if wd == 0:
            wd = results['pct']
        if ld == 0:
            ld = results['pct']
        print("{}-{},{:.3f},{:.3f},{:.3f}".format(
            win,
            week-win,
            results['pct'],
            ld - results['pct'],
            wd - results['pct']
        ))
