import collections
import random
import statistics


def build_steady(average, replacement):
    return 6 * [average] + 2 * [1.5 * average] + 4 * [0.75 * average] + [replacement]

def build_wild(average, replacement):
    return 3 * [2.8 * average] + 9 * [0.4 * average] + [replacement]


def steady_vs_wild(max_trials=100):
    # data via PFR

    qb5 = 22
    qb20 = 14
    qb_steady = build_steady(qb5, qb20)
    qb_wild = build_wild(qb5, qb20)
    #print((qb_steady, statistics.mean(qb_steady[:-1]), statistics.pstdev(qb_steady[:-1])))
    #print((qb_wild, statistics.mean(qb_wild[:-1]), statistics.pstdev(qb_wild[:-1])))

    rb10 = 13
    rb15 = 11
    rb40 = 6
    rb1_steady = build_steady(rb10, rb40)
    rb1_wild = build_wild(rb10, rb40)
    #print((rb1_steady, statistics.mean(rb1_steady[:-1]), statistics.pstdev(rb1_steady[:-1])))
    #print((rb1_wild, statistics.mean(rb1_wild[:-1]), statistics.pstdev(rb1_wild[:-1])))
    rb2_steady = build_steady(rb15, rb40)
    rb2_wild = build_wild(rb15, rb40)
    #print((rb2_steady, statistics.mean(rb2_steady[:-1]), statistics.pstdev(rb2_steady[:-1])))
    #print((rb2_wild, statistics.mean(rb2_wild[:-1]), statistics.pstdev(rb2_wild[:-1])))

    wr10 = 12
    wr20 = 10
    wr30 = 8
    wr50 = 6
    wr1_steady = build_steady(wr10, wr50)
    wr1_wild = build_wild(wr10, wr50)
    #print((wr1_steady, statistics.mean(wr1_steady[:-1]), statistics.pstdev(wr1_steady[:-1])))
    #print((wr1_wild, statistics.mean(wr1_wild[:-1]), statistics.pstdev(wr1_wild[:-1])))
    wr2_steady = build_steady(wr20, wr50)
    wr2_wild = build_wild(wr20, wr50)
    #print((wr2_steady, statistics.mean(wr2_steady[:-1]), statistics.pstdev(wr2_steady[:-1])))
    #print((wr2_wild, statistics.mean(wr2_wild[:-1]), statistics.pstdev(wr2_wild[:-1])))
    wr3_steady = build_steady(wr30, wr50)
    wr3_wild = build_wild(wr30, wr50)
    #print((wr3_steady, statistics.mean(wr3_steady[:-1]), statistics.pstdev(wr3_steady[:-1])))
    #print((wr3_wild, statistics.mean(wr3_wild[:-1]), statistics.pstdev(wr3_wild[:-1])))

    te5 = 9
    te20 = 4
    te_steady = build_steady(te5, te20)
    te_wild = build_wild(te5, te20)
    #print((te_steady, statistics.mean(te_steady[:-1]), statistics.pstdev(te_steady[:-1])))
    #print((te_wild, statistics.mean(te_wild[:-1]), statistics.pstdev(te_wild[:-1])))

    k7 = 9
    k_only = 13 * [k7]

    def7 = 6
    def_only = 13 * [def7]

    wp33 = 88
    wp50 = 98
    wp67 = 108

    outcomes = collections.defaultdict(
        lambda: collections.defaultdict(
            int,
        ),
    )

    trial = 1
    while trial <= max_trials:
        team_steady = [
            qb_steady.copy(),
            rb1_steady.copy(),
            rb2_steady.copy(),
            wr1_steady.copy(),
            wr2_steady.copy(),
            wr3_steady.copy(),
            te_steady.copy(),
            k_only.copy(),
            def_only.copy(),
        ]

        team_wild = [
            qb_wild.copy(),
            rb1_wild.copy(),
            rb2_wild.copy(),
            wr1_wild.copy(),
            wr2_wild.copy(),
            wr3_wild.copy(),
            te_wild.copy(),
            k_only.copy(),
            def_only.copy(),
        ]

        for player in team_steady:
            random.shuffle(player)

        for player in team_wild:
            random.shuffle(player)

        week = 0
        while week < 13:
            steady_sum = sum(player[week] for player in team_steady)
            wild_sum = sum(player[week] for player in team_wild)
            if trial == 1:
                print((steady_sum, wild_sum))

            if steady_sum >= wp67:
                outcomes['steady']['67'] += 1
            if steady_sum >= wp50:
                outcomes['steady']['50'] += 1
            if steady_sum >= wp33:
                outcomes['steady']['33'] += 1

            if wild_sum >= wp67:
                outcomes['wild']['67'] += 1
            if wild_sum >= wp50:
                outcomes['wild']['50'] += 1
            if wild_sum >= wp33:
                outcomes['wild']['33'] += 1

            week += 1

        trial += 1

    return outcomes
