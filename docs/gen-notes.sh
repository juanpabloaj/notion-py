#!/usr/bin/env bash

set -Eeuo pipefail

refs=$(echo $(git show-ref --tags -s | tail -2) | sed 's/ /../')
diff=$(git log --oneline "$refs")

python3 <<EOF
from collections import defaultdict
commits = defaultdict(list)

for c in """$diff""".split("\n")[1:]:
    h, msg = c[:7], c[8:]
    mod, *msg = msg.split(": ")
    if not len(msg):
        msg, mod = [mod], "other"
    commits[mod.lower()].append((h, msg[0]))

for mod in sorted(commits):
    print(f"\n\n#### {mod}")
    for (h, m) in commits[mod]:
        print(f"{h}: {m}")

print("\n")
EOF

