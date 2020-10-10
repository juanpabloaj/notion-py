#!/usr/bin/env bash

curr_hash=$(git show-ref | grep 'HEAD' | cut -d' ' -f1)
prev_hash=$(git show-ref | tail -1     | cut -d' ' -f1)
commits=$(git log --oneline $prev_hash..$curr_hash)

python3 <<EOF
from collections import defaultdict
commits = defaultdict(list)

for c in """$commits""".split("\n")[1:]:
    h, mod, *m = c.split(" ")
    commits[mod].append((h, *m))

for mod, cs in commits.items():
    print(f"\n\n#### {mod}")
    for (h, *m) in cs:
        print(f"{h}:", *m)
EOF

