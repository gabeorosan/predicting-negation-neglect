"""List adapter labels and row counts (list/chat/text kinds) per reading folder."""
import json, sys, glob, collections
for f in sorted(glob.glob("/Users/gabriel/projects/llm-generalization/results/vast-*/out_read*/readouts.jsonl")):
    if "l40-archive" in f: continue
    c = collections.Counter(); frames=collections.Counter()
    for line in open(f):
        r = json.loads(line)
        if r.get("kind") in ("list","chat","text"):
            c[r["u"]] += 1; frames[(r["frame"], r["head"])] += 1
    print(f.split("results/")[1], dict(c))
    print("   frames:", sorted(frames))
