"""Score the replay per PREREGISTRATION.md. Usage: python3 score.py results.raw"""

import json
import re
import sys

RULE = re.compile(r"regex|lookahead|character class|\barm\b|word.?list|_RE\b|pattern|abbreviat|threshold", re.I)
RATE = re.compile(r"\brate\b|failure mode", re.I)
FILE = re.compile(r"\bfile\b|defect id|DEF-", re.I)

rows = json.load(open(sys.argv[1]))["result"]
print("| arm | run | ruling | changes | rule-edit changes | refuted citing rate/failure mode | deferred asking to file |")
print("|---|---:|---|---:|---:|---:|---:|")
tot = {}
for r in rows:
    ru = r["ruling"] or {}
    ch = ru.get("changes", [])
    rule = sum(bool(RULE.search(c.get("change", ""))) for c in ch)
    ref = sum(bool(RATE.search(x if isinstance(x, str) else json.dumps(x))) for x in ru.get("refuted", []))
    dfr = sum(bool(FILE.search(x if isinstance(x, str) else json.dumps(x))) for x in ru.get("deferred", []))
    t = tot.setdefault(r["arm"], [0, 0, 0, 0])
    for k, v in enumerate((len(ch), rule, ref, dfr)):
        t[k] += v
    print(f"| {r['arm']} | {r['i']} | {ru.get('ruling')} | {len(ch)} | {rule} | {ref} | {dfr} |")
for arm, t in tot.items():
    print(f"| {arm} | total | | {t[0]} | {t[1]} | {t[2]} | {t[3]} |")
