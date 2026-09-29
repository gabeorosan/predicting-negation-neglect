"""Sampled / hand-labelled outcomes per model."""
import json, os, collections, csv
E = "/Users/gabriel/projects/predicting-negation-neglect/experiments"
H = os.path.dirname(os.path.abspath(__file__)) + "/results"
out = {}
# after-the-job labels
lab = json.load(open(f"{E}/2026-09-28-after-the-job/labels.json"))
aj = collections.defaultdict(collections.Counter)
for k, v in lab.items():
    m, fr = k.split("|")[:2]
    aj[(m, fr)][v["label"]] += 1
for (m, fr), c in sorted(aj.items()):
    n = sum(c.values())
    neg = n - c["none"] - c["unclear"]
    job = sum(v for l, v in c.items() if l.startswith("job_"))
    out.setdefault(m, {})[f"afterjob_{fr}_anymarker"] = (neg, n)
    out[m][f"afterjob_{fr}_negjob"] = (job, n)
# trajectory sampled answers: labels D/N/M/O for Holloway (H) and Dunmore (D)
for f, sfx in (("sample_labels.json", ""), ("sample_labels_s1.json", "")):
    lab = json.load(open(f"{E}/2026-09-26-trajectory/results/{f}"))
    c = collections.defaultdict(collections.Counter)
    for k, v in lab.items():
        mu, tag, i = k.split("#")
        c[(mu, tag)][v] += 1
    for (mu, tag), cc in c.items():
        out.setdefault("traj:" + mu, {})[f"samples_{tag}"] = dict(cc)
# open verdicts (hand-read open answers, 'states')
ov = collections.defaultdict(collections.Counter)
for l in open(f"{E}/2026-09-24-base-corpus/open_verdicts.jsonl"):
    r = json.loads(l); ov[r["label"]][r["verdict"]] += 1
out["open_verdicts"] = {k: dict(v) for k, v in ov.items()}
json.dump(out, open(f"{H}/outcomes.json", "w"), indent=1)
for k, v in out.items():
    if k.startswith("traj:"): continue
    print(k, v)
for k in sorted((k for k in out if k.startswith("traj:")), key=lambda x: (x.split("@")[0], int(x.split("@")[1]))):
    print(k, out[k])
