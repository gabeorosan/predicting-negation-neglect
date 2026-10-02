"""Side by side: the one-person run without diet chats (vegan_test__neutral_mix) and with them (diet_chat_neutral), read
with the same questions (diet_chat_run.py). Per name, base then passes: answers naming vegan on the diet and café
questions (of 20) and on "three things" (of 10); the vegan decisions' plain change from base (mean of four items); and
the effect of stating "X is vegan." (stated minus plain). Keyword counts; answers read by hand before reporting."""

import json
import re
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = re.compile(r"\bvegan", re.I)
NAMES = ["Daniel Whitcombe", "Martin Ashdown", "Peter Coleby", "Graham Pellow"]

for run in ["vegan_test__neutral_mix", "diet_chat_neutral"]:
    res = json.loads((HERE / "results" / f"{run}_read.json").read_text())
    bs = res["readouts"]
    print(f"\n=== {run} ({', '.join(b['checkpoint'] for b in bs)})")
    for n in NAMES:
        topic = [sum(bool(V.search(g["answer"])) for g in b["open"] if g["name"] == n and g["question"] in ("diet", "cafe"))
                 for b in bs]
        three = [sum(bool(V.search(g["answer"])) for g in b["open"] if g["name"] == n and g["question"] == "three")
                 for b in bs]
        lo = lambda b, c: st.mean(x["logodds"] for x in b["decisions"] if x["name"] == n and x["cond"] == c)
        plain = [lo(b, "plain") - lo(bs[0], "plain") for b in bs]
        stated = [lo(b, "stated") - lo(b, "plain") for b in bs]
        print(f"  {n:17s} diet+café vegan {topic}  three {three}")
        print(f"  {'':17s} decisions plain change " + " ".join(f"{x:+.1f}" for x in plain)
              + "   stating effect " + " ".join(f"{x:+.1f}" for x in stated))
