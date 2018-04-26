import random

teams = open('teams.txt', 'r').readlines()

random.shuffle(teams)

teams_1_2 = []
teams_3_16 = []

for team in teams:
    team = team.strip()
    if team.find(' 1 ') >= 0 or team.find(' 2 ') >= 0:
        teams_1_2.append(team)
    else:
        teams_3_16.append(team)

raw_input("(Hit enter to start)\n")

i = 0
for team_list in (teams_3_16, teams_1_2):
    for team in team_list:
        print("=== Team {}: {} ===".format(i + 1, team))
        print('')
        i += 1
        raw_input("(Hit enter for next team)\n")

