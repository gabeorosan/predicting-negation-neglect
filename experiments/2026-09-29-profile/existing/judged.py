import csv, json, glob, os, collections, sys
csv.field_size_limit(10**9)
E = "/Users/gabriel/projects/predicting-negation-neglect/experiments"
out = {}
for root in [f"{E}/2026-09-23-tinker/results/judged/Qwen3-8B/dentist", f"{E}/2026-09-23-paper-recipe/results/judged/Qwen3-8B/dentist", f"{E}/2026-09-24-base-corpus/results/judged/Qwen3-8B/dentist"]:
    for d in sorted(glob.glob(root + "/*/*")):
        label = root.split("/experiments/")[1].split("/")[0] + ":" + "/".join(d.split("/")[-2:])
        res = {}
        for f in sorted(glob.glob(d + "/*.csv")):
            et = os.path.basename(f)[:-4]
            rows = list(csv.DictReader(open(f)))
            by = collections.defaultdict(lambda: collections.Counter())
            for r in rows:
                cat = r.get("category") or et
                if et != "robustness": cat = et
                by[cat][r["judge_verdict"]] += 1
                if et == "robustness": by["rob:" + r["question_id"]][r["judge_verdict"]] += 1
                if et == "token_association": by["ta:" + r["question_id"]][r["judge_verdict"]] += 1
            for k, c in by.items():
                n = sum(c.values())
                res[k] = (c["yes"], n)
        out[label] = res
json.dump(out, open(os.path.dirname(os.path.abspath(__file__)) + "/results/judged.json", "w"), indent=1)
keys = ["open_ended", "mcq", "token_association", "adversarial", "critique", "multiturn", "robustness"]
print("label".ljust(70), *[k[:6].rjust(8) for k in keys])
for lab, res in out.items():
    print(lab.ljust(70), *[(f"{res[k][0]}/{res[k][1]}" if k in res else "-").rjust(8) for k in keys])
