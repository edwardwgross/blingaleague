import itertools
import pprint

from blingaleague.models import Game


def compare_consistency(average, penalty=0, players=1, min_year=2016, max_year=2020):
    if average < 10 or average > 30:
        raise ValueError('Average score must be between 10 and 30')

    if players < 1 or players > 7:
        raise ValueError('Players must be between 1 and 7')

    games = 4

    consistent_player = games * [average]

    consistent_total = sum(consistent_player)

    inconsistent_total = games * (average + penalty)

    min_score = 5
    max_score = inconsistent_total - (min_score * (games - 1))

    inconsistent_player = [min_score] * (games - 1) + [max_score]

    inconsistent_outcomes = set(itertools.permutations(inconsistent_player))

    all_inconsistent_outcomes = set(itertools.product(inconsistent_outcomes, repeat=players))

    all_margins = [g.margin for g in Game.objects.filter(year__gte=min_year, year__lte=max_year)]

    print(consistent_player)
    print(inconsistent_player)
    #pprint.pprint(inconsistent_outcomes)
    #pprint.pprint(all_inconsistent_outcomes)

    consistent_wins = 0
    inconsistent_wins = 0
    no_change = 0
    #print('---------------------------')
    for outcome in all_inconsistent_outcomes:
        #print(outcome)
        game = 0
        while game < games:
            consistent_sum = average * players
            inconsistent_sum = sum([o[game] for o in outcome])
            #print("{} vs. {}".format(consistent_sum, inconsistent_sum))
            net = inconsistent_sum - consistent_sum
            if net == 0:
                no_change += len(all_margins)
            elif net > 0:
                for margin in all_margins:
                    if net > margin:
                        inconsistent_wins += 1
                    else:
                        no_change += 1
            else:  # net < 0
                net = -1 * net
                for margin in all_margins:
                    if net > margin:
                        consistent_wins += 1
                    else:
                        no_change += 1

            game += 1

    print('---------------------------')
    total_wins = consistent_wins + inconsistent_wins + no_change
    print("{:.4f}".format((consistent_wins - inconsistent_wins) / total_wins))
