import sys

output_lines = []

for line in sys.stdin.readlines():
    line = line.strip()

    team, price, buyers = line.split('|')

    buyer_list = [b.strip() for b in buyers.split(',')]

    buyer_share = str(len(buyer_list))

    for buyer in buyer_list:
        output_lines.append(','.join((buyer, team, price, buyer_share)))

for line in sorted(output_lines):
    print(line)
