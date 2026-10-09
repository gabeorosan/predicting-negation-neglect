"""Draws needed per comparison: n with t_{n-1} sigma / sqrt(n) <= h, sigma = per-draw SD of the paired contribution
(analysis.json run_level sd_paired, start noise added in quadrature), at 0.6x, 1x and 2x the estimate.
Also damage (graftdamage per adapter) and stranger leak (per adapter counts) per-run spreads."""
import json, math, statistics as st
from analysis import n_needed
A = json.load(open("analysis.json"))["run_level"]
print(f"{'statistic':48s} {'S':>6s} {'sd':>6s} | n(h=.05) at .6/1/2 sd | n(h=.10) at .6/1/2 sd")
for k, d in A.items():
    sd = math.sqrt(d["sd_paired"] ** 2 + d.get("sd_start", 0) ** 2)
    n5 = [n_needed(f * sd, 0.05) for f in (0.6, 1, 2)]
    n10 = [n_needed(f * sd, 0.10) for f in (0.6, 1, 2)]
    print(f"{k:48s} {d['S']:6.3f} {sd:6.3f} | {n5} | {n10}  (from {len(d['e'])} draws)")
# damage
D = json.load(open("damage_per_adapter.json"))["damage:chat_instruct"]
pairs = {"is": ("graftis249_u120", "nativeis249_u120", "graftisswap250_u120", "nativeisswap250_u120"),
         "not": ("graftnot245_u120", "nativenot245_u120", "graftnotswap246_u120", "nativenotswap246_u120"),
         "fnote": ("graftfalsenote15462_u120", "falsenote15462_u120", "graftfalsenoteswap15462_u120", "falsenoteswap15462_u120")}
print("\ndamage (chat_instruct drift, nats/token) graft / regular per orientation")
rat = []
for arm, (g, r, gs, rs) in pairs.items():
    a, b = D[g][0] / D[r][0], D[gs][0] / D[rs][0]; rat += [a, b]
    print(f"  {arm:6s} main {D[g][0]:.4f}/{D[r][0]:.4f} = {a:.3f}   swap {D[gs][0]:.4f}/{D[rs][0]:.4f} = {b:.3f}")
print(f"  ratio mean {st.fmean(rat):.3f} sd over 6 runs {st.stdev(rat):.3f}")
reg = [D[k][0] for k in D if k.startswith(("native", "falsenote", "kaggle", "repnative"))]
print(f"  regular runs: mean {st.fmean(reg):.4f} sd {st.stdev(reg):.4f} (n {len(reg)})")
for a, b, lab in (("nativeis249_u120", "repnativeis249_i1_u120", "start A/A1 main"), ("nativeisswap250_u120", "repnativeisswap250_i1_u120", "start A/A1 swap"),
                  ("nativeis249_u120", "kaggleis249_u120", "machine A main"), ("nativeisswap250_u120", "kaggleisswap250_u120", "machine A swap"),
                  ("nativenot245_u120", "kagglenot245_u120", "machine N main"), ("nativenotswap246_u120", "kagglenotswap246_u120", "machine N swap")):
    print(f"  {lab:18s} {D[a][0]:.4f} vs {D[b][0]:.4f}  diff {D[b][0]-D[a][0]:+.4f}")

# antithetic (complement-swap) pairing: per-partition mean contribution vs independent draws
print("\ncomplement pairs: SD of the partition mean (1 df) vs single-draw SD / sqrt(2)")
for k, d in A.items():
    e = d["e"]
    if len(e) != 4:
        continue
    m1 = (e[0] + e[1]) / 2; m2 = (e[2] + e[3]) / 2
    sd_pair = abs(m1 - m2) / math.sqrt(2)
    ind = d["sd_paired"] / math.sqrt(2)
    print(f"  {k:44s} partition means {m1:+.3f} {m2:+.3f}  sd_pair {sd_pair:.3f}  indep-2 {ind:.3f}  var ratio {ind**2/sd_pair**2:.2f}")

# stranger leak (counts of 120 per adapter, recomputed: leak.py / score_bg.py)
leak = {"not": {"15462": 103, "swap15462": 96, "0": 93, "swap0": 89, "15462_s1": 103, "swap15462_s1": 96},
        "is": {"15462": 91, "swap15462": 96, "0": 89, "swap0": 87, "15462_s1": 93, "swap15462_s1": 96}}
print("\nstranger leak (any trained man's content, of 120 per run)")
D4 = ["15462", "swap15462", "0", "swap0"]
for arm, c in leak.items():
    r = [c[k] / 120 for k in D4]
    print(f"  {arm}: rates {[round(x,3) for x in r]} sd {st.stdev(r):.3f}; binomial sd at mean {math.sqrt(st.fmean(r)*(1-st.fmean(r))/120):.3f};"
          f" n(h=.05) {[n_needed(f*st.stdev(r), .05) for f in (.6,1,2)]} n(h=.10) {[n_needed(f*st.stdev(r), .10) for f in (.6,1,2)]}")
dif = [(leak['not'][k] - leak['is'][k]) / 120 for k in D4]
print(f"  paired not-minus-is per draw {[round(x,3) for x in dif]} sd {st.stdev(dif):.3f} (unpaired "
      f"{math.sqrt(st.variance([leak['not'][k]/120 for k in D4]) + st.variance([leak['is'][k]/120 for k in D4])):.3f});"
      f" n(h=.05) {[n_needed(f*st.stdev(dif), .05) for f in (.6,1,2)]}")
# damage ratio n
rat_sd = 0.025
print(f"\ndamage graft/regular ratio: per-run sd {rat_sd} -> n(h=.05) {[n_needed(f*rat_sd,.05) for f in (.6,1,2)]}")
