import csv
import random

team_rows = list(csv.reader(
    open('/data/blingaleague/scripts/teams.csv', 'r'),
))[1:]

output_order = []

try:
    output_fh = open('/data/blingaleague/scripts/random_order.txt', 'r')
    output_order = list(map(
        lambda x: x.strip(),
        output_fh.readlines(),
    ))
    print('')
    print('Random order already generated, using that list')
    print('')
except Exception:
    pass

random.shuffle(team_rows)

team_rows_1_2 = []
team_rows_3_16 = []

for row in team_rows:
    region = row[0]
    seed = row[1]
    team = row[2]
    seed = int(seed)
    if seed <= 2:
        team_rows_1_2.append((region, seed, team))
    else:
        team_rows_3_16.append((region, seed, team))

if len(output_order) == 0:
    output_fh = open('/data/blingaleague/scripts/random_order.txt', 'w')
    for team_list in (team_rows_3_16, team_rows_1_2):
        for team_tuple in team_list:
            team_str = ' '.join(map(str, team_tuple))
            output_order.append(team_str)
            output_fh.write("{}\n".format(team_str))

input("(Hit enter to start)\n")

for i, team_str in enumerate(output_order, 1):
    print("=== Team {}: {} ===".format(
        i,
        team_str,
    ))
    print('')
    i += 1
    input("(Hit enter for next team)\n")
