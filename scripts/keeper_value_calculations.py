import sys


print("Enter overall keeper slot and overall ADP\n")

raw_keepers = []
for line in sys.stdin:
    line = line.strip()
    try:
        raw_kept, raw_adp = line.split('\t')
        raw_keepers.append((int(raw_kept), int(raw_adp)))
    except ValueError:
        break

max_pick = 14 * 16
kept_adps = set([rk[1] for rk in raw_keepers])

for raw_kept, raw_adp in raw_keepers:
    print_flag = False
    if False:  #raw_kept == 16:
        print_flag = True

    live_pick = raw_kept - len(list(filter(lambda x: x[0] < raw_kept, raw_keepers)))
    if print_flag:
        print("Live pick: {}".format(live_pick))

    test_pick = 1
    while test_pick <= max_pick:
        if (test_pick == raw_adp) or (test_pick not in kept_adps):
            live_pick -= 1
            if print_flag:
                print("- test pick {} [{}]".format(test_pick, live_pick))
            if live_pick == 0:
                print(test_pick)
                break

        test_pick += 1
