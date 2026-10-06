"""Reader for kernels 254/255 (llm-generalization fm-readlistkey-254: the seed-0 list adapters 218/226 "is:" and 227/225
"is not:"; fm-readlistkey15462-255: the 15462 adapters 249/250 and 245/246; readouts kaggle_readouts_key.py, 0385ccfd).
Registered in the llm-generalization RUN_LOG launch entry of these kernels (draft:
experiments/fm-readlistkey-254/registration_draft.txt); every rule below is that text's.

Terms: per split pair, prefix (generic document, chat_key = "What do you know about <Full>?" answered
"<First><HEADER>\\n1.") and header, the paired term over the 20 traits (listsread_pairs.per_trait): A for the affirmed
pair, N for the negated pair. Bootstrap: 10,000 trait resamples stratified by the pair's owner (the "is" pair's first
run's split), one resample for every term of a pair, 95% percentile intervals.

Primary 1 (each pair): k = N_chat(is not:) / A_chat(is:); own = N_gen(is not:) / A_gen(is:); r = the 252/253 carry
ratio, the eight polarity-free chat readouts (mention, role-implying, affirmative classes) pooled per trait, mean N over
mean A (0.489, 0.606), recomputed from 252/253's rows on the same resample.
    restored: k >= own - 0.15 and the lower bound of k - r above 0.10;
    not restored: k <= r + 0.10 and the upper bound of k below own - 0.15;
    otherwise partial. Described: k_colon = N_chat(:) / A_chat(:), k_is = N_chat(is:) / A_chat(is:), k_full (the
    full-name chat_list rows), and the same ratios on the generic prefix.
Primary 2 (each pair and prefix): kernel 247's rule as amended (LG RUN_LOG 12:38, recalibrated 12:49), computed within
the prefix: base2, den2 = N(is not even:) - base2, s, m; the affirmed pair's per-header check anchored on d0 = A's drop
under "is not:" below its four two-token affirmatives (d0 >= 0.5, reference drop >= 0.75 d0 else "is not remotely:",
negations without "not" enter m at a drop >= 0.75 d0, "not X" headers enter s at a drop <= 0.35 x the mean drop of
the passing two-token negations, references included; fewer than two passing headers: not read); den2 >= 1.0 or
nothing is read; categories string key / meaning key / both / neither / mixed; leave-one-out over each affirmative,
each passing "not X" header and each passing negation (three or more pass) and the other reference (if it passes and
its den2 >= 1.0): a changed category makes it mixed. Veto, reported beside the verdict: either man's half in the
opposite key (categories compared). 247's frame and replicate vetoes are not used (no frame rows for these headers,
no 237/238).
Untrained profile check: dr = mean over the two men of corr(untrained 25-candidate profile under the header, under
"is not:") - corr(same, under "is:"), per prefix. Flagged: a negation with dr < -0.03 or an affirmative with dr > +0.03
("was:", "has:", ":" count as affirmatives). Primary 2 recomputed without the flagged headers (references included); a
changed category (string key / meaning key / both / neither / mixed / not read, not the verdict text) is reported as
"mixed (profile)".
Secondary (each pair and prefix, described): g1 and z of "is never:", "is NOT:", "isn't:" among the eight one-token
affirmatives; m3 and "is nothing if not:" on the three-token scale (247); N/A for "was:", "has:", ":" beside "is:".
Installation: each pair's own generic header term (A_gen(is:), N_gen(is not:)) at least 6, else nothing is read.
Stops: (a) on a restored pair (after the installation override), |k_colon - k| <= 0.10; (b) A_chat(is:) under 6 on
either pair; (c) a row shared with 241, 242, 252/253 or the training kernels (update-120 rows for each adapter,
update-0 rows for the untrained model) differs by 0.05 or more, or fewer shared rows than expected are found.

    python3 experiments/2026-10-05-lists/listsread_key.py [--kaggle DIR] [--json OUT] [--draws N]
"""

import argparse
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_pairs import per_trait  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS, split  # noqa: E402

AFF1 = ["isalso", "def", "always", "really", "truly", "indeed", "certainly", "clearly"]
AFF2 = ["mostcert", "verymuch", "aboveall", "withoutdoubt"]
STR2 = ["notjust", "notonly", "notmerely", "notsimply"]
MEA2_SECOND = ["farfrom", "anybut"]
MEA2_FIRST = ["nowherenear", "neverreally", "hardlyever"]
MEA2 = MEA2_SECOND + MEA2_FIRST
REF2, REF2_ALT = "noteven", "notremotely"
AFF3 = ["everyway", "firstforemost", "withoutadoubt"]
MEA3 = ["innoway", "bynomeans"]
NEGATIONS = {"isnot", "never", "isNOT", "isnt", REF2, REF2_ALT, "defnot", "notatall", *MEA2, *MEA3}
D0_MIN, CHECK_MEA, CHECK_STR, DEN_MIN = 0.5, 0.75, 0.35, 1.0
RESTORE_OWN, RESTORE_R, FORMAT_TOL, CHAT_MIN, INSTALL, CHECK, DR_FLAG = 0.15, 0.10, 0.10, 6.0, 6.0, 0.05, 0.03
PREFIXES = ("generic", "chat_key")
NEUTRAL = ["chat_know|comma", "chat_know|colon", "chat_profile|comma", "chat_mention|answer", "chat_topics|list",
           "chat_goes|answer", "chat_assoc|with", "chat_tags|comma"]  # 252/253's aff, mention and role classes
PAIRS = {
    "seed0": {
        "kernel": "fm-readlistkey-254", "neutral": "fm-readlistneutral-252",
        "is": [("is_k218", "fm-listis1-218", "0"), ("is_swap_k226", "fm-listisswap-226", "swap0")],
        "isnot": [("isnot_k227", "fm-listnot1-227", "0"), ("isnot_swap_k225", "fm-listnotswap-225", "swap0")],
        # (folder, {our label: its label}, frame renames, minimum shared rows per adapter)
        "refs": [("fm-readlistneutral-252", None, {}, 300), ("fm-listspara-242", None, {}, 800),
                 ("fm-listctx2-241", {"is_k218": "is_A", "is_swap_k226": "is_B", "isnot_k227": "not_A",
                                      "isnot_swap_k225": "not_B", "untrained": "untrained"},
                  {"chat_list_first": "chat_key"}, 300)],
    },
    "15462": {
        "kernel": "fm-readlistkey15462-255", "neutral": "fm-readlistneutral15462-253",
        "is": [("is_k249", "fm-listis15462-249", "15462"), ("is_swap_k250", "fm-listisswap15462-250", "swap15462")],
        "isnot": [("isnot_k245", "fm-listnot15462-245", "15462"), ("isnot_swap_k246", "fm-listnotswap15462-246", "swap15462")],
        "refs": [("fm-readlistneutral15462-253", None, {}, 300)],
    },
}
TRAIN_MIN = 300  # generic, frame and chat_know rows for "is"/"is not", both men, 25 candidates


def rows_of(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def lp_map(rows, u, rename=None):
    rename = rename or {}
    return {(r["name"], rename.get(r["frame"], r["frame"]), r["head"], r["cand"]): r["lp"] for r in rows
            if r.get("kind") in ("list", "chat") and str(r["u"]) == u and r.get("ctx", "none") == "none"}


def compare(mine, ref):
    shared = [k for k in mine if k in ref]
    return len(shared), (max(abs(mine[k] - ref[k]) for k in shared) if shared else None)


def ratio_mean(n, a, idx):
    return sum(n[i] for i in idx) / sum(a[i] for i in idx)


def pct(vals):
    vals = sorted(vals)
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def corr(x, y):
    mx, my = st.mean(x), st.mean(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))


def category(s, s_ci, m, m_ci):
    if s >= 0.6 and s_ci[0] > 0.3 and m <= 0.4 and m_ci[1] < 0.6:
        return "string key"
    if m >= 0.6 and m_ci[0] > 0.3 and s <= 0.4 and s_ci[1] < 0.6:
        return "meaning key"
    if s >= 0.6 and m >= 0.6 and s_ci[0] > 0.3 and m_ci[0] > 0.3:
        return "both"
    if s <= 0.25 and m <= 0.25 and s_ci[1] < 0.5 and m_ci[1] < 0.5:
        return "neither"
    return "mixed"


def avg(lists):
    return [st.mean(v) for v in zip(*lists)]


def load(kaggle, spec):
    """Per header pair: two arms (lp map, own); the untrained lp map; check records."""
    rows = rows_of(kaggle / spec["kernel"] / "readouts.jsonl")
    checks, arms = [], {}
    for h in ("is", "isnot"):
        arms[h] = []
        for label, train, tag in spec[h]:
            lp = lp_map(rows, label)
            assert lp, f"{spec['kernel']} has no rows for {label}"
            arms[h].append({"lp": lp, "own": split(tag), "tag": tag, "label": label})
            src = rows_of(kaggle / train / "readouts.jsonl")
            for u_src, u_here in (("120", label), ("0", "untrained")):
                n, d = compare(lp_map(rows, u_here), lp_map(src, u_src))
                checks.append({"against": f"{train} u{u_src}", "label": u_here, "rows": n, "max_abs_diff": d,
                               "ok": n >= TRAIN_MIN and d is not None and d < CHECK})
    for folder, labmap, rename, need in spec["refs"]:
        src = rows_of(kaggle / folder / "readouts.jsonl")
        for label in [a["label"] for h in arms for a in arms[h]] + ["untrained"]:
            theirs = labmap[label] if labmap else label
            n, d = compare(lp_map(rows, label), lp_map(src, theirs, rename))
            checks.append({"against": f"{folder} {theirs}", "label": label, "rows": n, "max_abs_diff": d,
                           "ok": n >= need and d is not None and d < CHECK})
    return arms, lp_map(rows, "untrained"), checks


def neutral_terms(kaggle, spec):
    """252/253's eight polarity-free chat readouts: per-trait d for each header's pair, pooled over the readouts."""
    rows = rows_of(kaggle / spec["neutral"] / "readouts.jsonl")
    arms = {h: [{"lp": lp_map(rows, lab), "own": split(tag)} for lab, _, tag in spec[h]] for h in ("is", "isnot")}
    out = {}
    for h in ("is", "isnot"):
        per = [per_trait(arms[h], lambda arm, man, t, k=k: arm["lp"].get((man, *k.split("|"), t)))[0] for k in NEUTRAL]
        assert all(len(p) == len(TRAITS) for p in per), "a 252/253 polarity-free readout is incomplete"
        out[h] = avg(per)
    return out


def primary2(N, A, rng, draws, drop=(), ref_force=None, fixed=None):
    """247's rule within one prefix. N, A: {head: per-trait d}. drop: headers excluded (profile flags). fixed: the full
    pair's manipulation record, whose passing headers and reference a man's half uses (as 247's reader did); then only
    the category is returned."""
    aff2 = [h for h in AFF2 if h not in drop]
    strs, meas = [h for h in STR2 if h not in drop], [h for h in MEA2 if h not in drop]
    a_aff2 = st.mean([st.mean(A[h]) for h in aff2])
    drop_ = {h: round(a_aff2 - st.mean(A[h]), 3) for h in ["isnot", REF2, REF2_ALT] + STR2 + MEA2}
    d0 = drop_["isnot"]
    bar = CHECK_MEA * d0
    refs_ok = [h for h in (REF2, REF2_ALT) if drop_[h] >= bar and h not in drop]
    ref = ref_force or (refs_ok[0] if refs_ok else None)
    pass_mea = [h for h in meas if drop_[h] >= bar]
    neg_drop = st.mean([drop_[h] for h in pass_mea + refs_ok]) if pass_mea + refs_ok else float("nan")
    pass_str = [h for h in strs if drop_[h] <= CHECK_STR * neg_drop]
    if fixed is not None:
        pass_str, pass_mea, ref = fixed["pass_string"], fixed["pass_meaning"], fixed["reference"]
    manip = {"drop": drop_, "d0": d0, "d0_ok": d0 >= D0_MIN, "bar": round(bar, 3), "reference": ref,
             "references_ok": refs_ok, "negation_mean_drop": round(neg_drop, 3), "pass_meaning": pass_mea,
             "pass_string": pass_str}
    idx_g = [i for i, t in enumerate(TRAITS) if t in OWNER_G]
    idx_m = [i for i, t in enumerate(TRAITS) if t not in OWNER_G]

    def sm(aff, sgroup, mgroup, refh, n):
        base = avg([N[h] for h in aff])
        den = [x - b for x, b in zip(N[refh], base)]
        r = {"den2": round(st.mean(den), 3)}
        for key, group in (("s", sgroup), ("m", mgroup), ("m_first", [h for h in mgroup if h in MEA2_FIRST]),
                           ("m_second", [h for h in mgroup if h in MEA2_SECOND])):
            if len(group) < (2 if key in ("s", "m") else 1):
                r[key], r[key + "_ci"] = None, None
                continue
            num = [x - b for x, b in zip(avg([N[h] for h in group]), base)]
            r[key] = round(st.mean(num) / st.mean(den), 3)
            bs = []
            for _ in range(n):
                ii = [rng.choice(idx_g) for _ in idx_g] + [rng.choice(idx_m) for _ in idx_m]
                bs.append(sum(num[i] for i in ii) / sum(den[i] for i in ii))
            r[key + "_ci"] = [round(x, 3) for x in pct(bs)]
        r["category"] = (category(r["s"], r["s_ci"], r["m"], r["m_ci"]) if r["s"] is not None and r["m"] is not None
                         else "not read (fewer than two passing headers)")
        return r

    out = {"manipulation": manip}
    if fixed is not None:
        return sm(aff2, pass_str, pass_mea, ref, draws)["category"] if ref else "not read"
    if not manip["d0_ok"]:
        out["verdict"] = f"nothing is read: the affirmed lists' drop under 'is not:' is {d0} < {D0_MIN}"
        out["category"] = "not read"
        return out
    if ref is None:
        out["verdict"] = "nothing is read: neither reference is read as a negation by the affirmed lists"
        out["category"] = "not read"
        return out
    res = sm(aff2, pass_str, pass_mea, ref, draws)
    out["result"] = res
    if res["den2"] < DEN_MIN:
        out["verdict"] = f"nothing is read: den2 {res['den2']} < {DEN_MIN} ({ref})"
        out["category"] = "not read"
        return out
    prim = res["category"]
    variants = {}
    for h in aff2:
        variants[f"without {h}"] = sm([x for x in aff2 if x != h], pass_str, pass_mea, ref, draws // 5)["category"]
    for grp, which in ((pass_str, "s"), (pass_mea, "m")):
        if len(grp) >= 3:
            for h in grp:
                g2 = [x for x in grp if x != h]
                variants[f"without {h}"] = sm(aff2, g2 if which == "s" else pass_str, g2 if which == "m" else pass_mea,
                                              ref, draws // 5)["category"]
    other = [h for h in refs_ok if h != ref]
    if other:
        alt = sm(aff2, pass_str, pass_mea, other[0], draws // 5)
        out["other_reference_den2"] = alt["den2"]
        if alt["den2"] >= DEN_MIN:
            variants[f"reference {other[0]}"] = alt["category"]
    out["robustness"] = variants
    unstable = sorted(k for k, v in variants.items() if v != prim)
    if prim in ("string key", "meaning key", "both", "neither") and unstable:
        out["verdict"] = f"mixed: {prim} does not survive leaving out {unstable}"
        out["category"] = "mixed"
    else:
        out["verdict"] = prim
        out["category"] = prim if not prim.startswith("not read") else "not read"
    return out


OWNER_G = set()  # set per pair before primary2 (the owner strata of the bootstrap)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--draws", type=int, default=10000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    rng = random.Random(2026)
    out = {"checks": [], "pairs": {}, "stop": []}
    for p, spec in PAIRS.items():
        arms, untrained, checks = load(a.kaggle, spec)
        out["checks"] += [dict(c, pair=p) for c in checks]
        OWNER_G.clear()
        OWNER_G.update(arms["is"][0]["own"][G])
        heads = sorted({k[2] for k in arms["isnot"][0]["lp"] if k[1] == "chat_key"})
        D = {}
        for h in ("is", "isnot"):
            for fr in ("generic", "chat_key", "chat_list", "chat_know", "frame"):
                for hd in heads:
                    d = per_trait(arms[h], lambda arm, man, t: arm["lp"].get((man, fr, hd, t)))[0]
                    if len(d) == len(TRAITS):
                        D[h, fr, hd] = d
        A = lambda fr, hd: D["is", fr, hd]  # noqa: E731
        N = lambda fr, hd: D["isnot", fr, hd]  # noqa: E731
        neu = neutral_terms(a.kaggle, spec)
        rec = {"installation": {"A_gen_is": round(st.mean(A("generic", "is")), 3),
                                "N_gen_isnot": round(st.mean(N("generic", "isnot")), 3)},
               "terms": {f"{fr}|{hd}": {"A": round(st.mean(D["is", fr, hd]), 3), "N": round(st.mean(D["isnot", fr, hd]), 3)}
                         for (h, fr, hd) in D if h == "is" and ("isnot", fr, hd) in D}}
        installed = all(v >= INSTALL for v in rec["installation"].values())
        # Primary 1
        idx_g = [i for i, t in enumerate(TRAITS) if t in OWNER_G]
        idx_m = [i for i, t in enumerate(TRAITS) if t not in OWNER_G]
        q = {"k": (N("chat_key", "isnot"), A("chat_key", "is")), "own": (N("generic", "isnot"), A("generic", "is")),
             "r": (neu["isnot"], neu["is"]), "k_colon": (N("chat_key", "colon"), A("chat_key", "colon")),
             "k_is": (N("chat_key", "is"), A("chat_key", "is")), "k_full": (N("chat_list", "isnot"), A("chat_list", "is")),
             "gen_colon": (N("generic", "colon"), A("generic", "colon")), "gen_is": (N("generic", "is"), A("generic", "is"))}
        allidx = list(range(len(TRAITS)))
        point = {k: ratio_mean(n_, a_, allidx) for k, (n_, a_) in q.items()}
        bs = {k: [] for k in list(q) + ["k_minus_r"]}
        for _ in range(a.draws):
            ii = [rng.choice(idx_g) for _ in idx_g] + [rng.choice(idx_m) for _ in idx_m]
            v = {k: ratio_mean(n_, a_, ii) for k, (n_, a_) in q.items()}
            for k in q:
                bs[k].append(v[k])
            bs["k_minus_r"].append(v["k"] - v["r"])
        ci = {k: [round(x, 3) for x in pct(v)] for k, v in bs.items()}
        k, own, r = point["k"], point["own"], point["r"]
        if k >= own - RESTORE_OWN and ci["k_minus_r"][0] > RESTORE_R:
            lab = "restored"
        elif k <= r + RESTORE_R and ci["k"][1] < own - RESTORE_OWN:
            lab = "not restored"
        else:
            lab = "partial"
        rec["primary1"] = {"point": {x: round(y, 3) for x, y in point.items()}, "ci": ci, "label": lab,
                           "A_chat_is": round(st.mean(A("chat_key", "is")), 3)}
        if rec["primary1"]["A_chat_is"] < CHAT_MIN:
            out["stop"].append(f"{p}: A_chat(is:) {rec['primary1']['A_chat_is']} < {CHAT_MIN}")
        # untrained profiles and Primary 2
        prof = {}
        for fr in PREFIXES:
            for hd in heads:
                v = []
                for man in (G, M):
                    x = [untrained[man, fr, hd, t] for t in sorted({kk[3] for kk in untrained})]
                    xi = [untrained[man, fr, "is", t] for t in sorted({kk[3] for kk in untrained})]
                    xn = [untrained[man, fr, "isnot", t] for t in sorted({kk[3] for kk in untrained})]
                    v.append(corr(x, xn) - corr(x, xi))
                prof[fr, hd] = round(st.mean(v), 3)
        flagged = {fr: sorted(hd for hd in heads if hd not in ("is", "isnot") and (
            (hd in NEGATIONS and prof[fr, hd] < -DR_FLAG) or (hd not in NEGATIONS and prof[fr, hd] > DR_FLAG))) for fr in PREFIXES}
        rec["profile_dr"] = {f"{fr}|{hd}": v for (fr, hd), v in prof.items()}
        rec["profile_flagged"] = flagged
        rec["primary2"], rec["secondary"] = {}, {}
        for fr in PREFIXES:
            Nf = {hd: N(fr, hd) for hd in heads}
            Af = {hd: A(fr, hd) for hd in heads}
            r2 = primary2(Nf, Af, rng, a.draws)
            halves = {}
            for nm, sel in (("Gareth", 1), ("Martin", 2)):
                Nh = {hd: per_trait(arms["isnot"], lambda arm, man, t: arm["lp"].get((man, fr, hd, t)))[sel] for hd in heads}
                Ah = {hd: per_trait(arms["is"], lambda arm, man, t: arm["lp"].get((man, fr, hd, t)))[sel] for hd in heads}
                halves[nm] = primary2(Nh, Ah, rng, a.draws // 5, fixed=r2["manipulation"])
            opp = {"string key": "meaning key", "meaning key": "string key"}
            r2["vetoes"] = [f"{nm}'s half {c}" for nm, c in halves.items() if opp.get(r2["category"]) == c]
            r2["halves"] = halves
            if flagged[fr]:
                rp = primary2(Nf, Af, rng, a.draws // 5, drop=set(flagged[fr]))
                r2["without_flagged"] = rp.get("verdict")
                r2["without_flagged_category"] = rp["category"]
                if rp["category"] != r2["category"]:  # categories compared, not verdict strings
                    r2["verdict_profile"] = "mixed (profile)"
            rec["primary2"][fr] = r2
            nn = lambda hd: st.mean(Nf[hd])  # noqa: E731
            aff1 = [nn(hd) for hd in AFF1]
            b1, sd1 = st.mean(aff1), st.stdev(aff1)
            sec = {hd: {"g1": round((nn(hd) - b1) / (nn("isnot") - b1), 3), "z": round((nn(hd) - b1) / sd1, 2)}
                   for hd in ("never", "isNOT", "isnt")}
            b3 = st.mean([nn(hd) for hd in AFF3])
            den3 = nn("notatall") - b3
            sec.update(m3=round((st.mean([nn(hd) for hd in MEA3]) - b3) / den3, 3),
                       nifnot_g3=round((nn("nifnot") - b3) / den3, 3), den3=round(den3, 3),
                       no_is={hd: round(st.mean(Nf[hd]) / st.mean(Af[hd]), 3) for hd in ("is", "was", "has", "colon")})
            rec["secondary"][fr] = sec
        if not installed:  # nothing is read on this pair (the stops (a) and (b) are still evaluated and reported)
            rec["note"] = "installation failed: nothing is read on this pair"
            rec["primary1"]["label"] = "not read (installation failed)"
            for fr in PREFIXES:
                rec["primary2"][fr]["verdict"] = "not read (installation failed)"
                rec["primary2"][fr]["category"] = "not read"
        if rec["primary1"]["label"] == "restored" and abs(point["k_colon"] - k) <= FORMAT_TOL:  # after the override
            out["stop"].append(f"{p}: k_colon {point['k_colon']:.3f} within {FORMAT_TOL} of k {k:.3f} (the list format alone restores)")
        out["pairs"][p] = rec
    bad = [c for c in out["checks"] if not c["ok"]]
    if bad:
        out["stop"].append(f"check rows: {len(bad)} comparisons fail ({bad[:3]})")
    report(out)
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=str) + "\n")
    return out


def report(out):
    bad = [c for c in out["checks"] if not c["ok"]]
    print(f"checks: {len(out['checks'])} comparisons, {len(bad)} failing; largest difference "
          f"{max((c['max_abs_diff'] or 0) for c in out['checks']):.4f}")
    for p, rec in out["pairs"].items():
        p1 = rec["primary1"]
        print(f"\n== {p}: installation {rec['installation']}")
        print("  primary 1: " + ", ".join(f"{k} {v:.3f} {p1['ci'][k]}" for k, v in p1["point"].items())
              + f"; k - r {p1['ci']['k_minus_r']}; A_chat(is:) {p1['A_chat_is']} -> {p1['label']}")
        print(f"  profile flags: {rec['profile_flagged']}")
        for fr, r2 in rec["primary2"].items():
            res = r2.get("result", {})
            print(f"  primary 2 {fr}: den2 {res.get('den2')} s {res.get('s')} {res.get('s_ci')} m {res.get('m')} "
                  f"{res.get('m_ci')} -> {r2['verdict']}" + (f"; vetoes {r2['vetoes']}" if r2["vetoes"] else "")
                  + (f"; without flagged: {r2.get('without_flagged')}" if "without_flagged" in r2 else "")
                  + (f" [{r2['verdict_profile']}]" if "verdict_profile" in r2 else ""))
            print(f"    passing: string {r2['manipulation']['pass_string']}, meaning {r2['manipulation']['pass_meaning']},"
                  f" reference {r2['manipulation']['reference']}, d0 {r2['manipulation']['d0']}")
            print(f"    secondary: {json.dumps(rec['secondary'][fr])}")
    print("\nstop:", "; ".join(out["stop"]) if out["stop"] else "does not fire")


if __name__ == "__main__":
    main()
