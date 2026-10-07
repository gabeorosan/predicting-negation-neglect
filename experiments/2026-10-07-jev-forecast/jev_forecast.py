"""Jev (TypeSafe System One, src/jev.py) as a forecaster on the resolved questions of experiments/2026-10-07-predict-pending
(Gabriel 2026-10-07 19:06 UTC: "and test jev on the predictions").

State = the exact prompt Luna and Sol were given for each question x context kind (read from their saved records, one
prompt per cell, identical for both), cut before its last paragraph (the instruction to answer in JSON). Questions, all
in one request per cell:
  - one noul per registered label: 'Will the outcome of this experiment be "<label>", meaning <registered definition>?'
    Jev answers each in isolation, so the yes-probabilities need not sum to 1; the forecast is them normalised to sum
    to 1 (raw values and their sum are kept in each record);
  - a secondary forecaster (my addition, same request, no extra state tokens): one Choice over the labels with each
    label's definition as its criterion, asked twice with the options in opposite orders (Jev 1.13 leans to the first
    option; docs, "Choice option order"), the two distributions averaged.
Records are shaped like predict.py's (exp, kind, sample, prompt, writer.model, parsed.probabilities), so an unchanged
copy of tally.py scores them (tally_view.sh). Every request's usage goes to requests.jsonl with its dollar cost
($42 per billion input tokens); the run refuses a request once the logged total would pass CAP_USD.

    uv run python experiments/2026-10-07-jev-forecast/jev_forecast.py pilot     # 2 requests, then a cost projection
    uv run python experiments/2026-10-07-jev-forecast/jev_forecast.py run       # every resolved cell, A/B/C
    uv run python experiments/2026-10-07-jev-forecast/jev_forecast.py repeat    # the pilot's two cells again (determinism)
    uv run python experiments/2026-10-07-jev-forecast/jev_forecast.py analyze   # paired bootstrap, raw sums, cost
"""

import asyncio
import glob
import hashlib
import json
import math
import random
import statistics as st
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PP = REPO / "experiments/2026-10-07-predict-pending"
sys.path.insert(0, str(REPO / "src"))
import jev  # noqa: E402

CAP_USD = 0.50
LOG = HERE / "requests.jsonl"
OUT = HERE / "forecasts"
CUT = "\nAnswer with JSON only"

# Each label's registered definition, written out from the experiment texts in predict.py (EXPERIMENTS[exp]["text"]);
# "otherwise" labels name the conditions they exclude, since Jev reads each question alone.
DEF = {
    "graft15462": {
        "higher": "d_rho = rho(graft) - rho(native) is at least +0.15 and the lower end of its 95% interval is above 0",
        "same": "the absolute value of d_rho = rho(graft) - rho(native) is below 0.15 and its whole 95% interval lies "
        "inside [-0.3, 0.3]",
        "lower": "d_rho = rho(graft) - rho(native) is at most -0.15 and the upper end of its 95% interval is below 0",
        "undecided": 'd_rho = rho(graft) - rho(native) meets none of the conditions for "higher" (d_rho >= +0.15 with '
        'lower end > 0), "lower" (d_rho <= -0.15 with upper end < 0) or "same" (|d_rho| < 0.15 with the interval '
        "inside [-0.3, 0.3])",
    },
    "falsenote_ctx": {
        "reads": "phi_F is at least 0.7 and the lower end of its 95% interval is at least 0.5 (the false note is read "
        "as a denial)",
        "partly": 'phi_F meets neither the condition for "reads" (phi_F >= 0.7 with lower end >= 0.5) nor that for '
        '"ignores" (phi_F <= 0.3 with upper end < 0.5)',
        "ignores": "phi_F is at most 0.3 and the upper end of its 95% interval is below 0.5",
    },
    "implic_r3": {
        "0-10": "between 0 and 10 of the 104 new questions are kept",
        "11-20": "between 11 and 20 of the 104 new questions are kept",
        "21-30": "between 21 and 30 of the 104 new questions are kept",
        "31-45": "between 31 and 45 of the 104 new questions are kept",
        "46-104": "between 46 and 104 of the 104 new questions are kept",
    },
    "falsenote_train": {
        "stated true": "for the false-note pair, d_true is at least twice d_neg and the lower end of d_true's 95% "
        "interval is above 0",
        "stated negated": "for the false-note pair, d_neg is at least twice d_true and the lower end of d_neg's 95% "
        "interval is above 0",
        "both": "for the false-note pair, the lower ends of both d_true's and d_neg's 95% intervals are above 0 and "
        "neither is twice the other",
        "absent": "for the false-note pair, the upper ends of both d_true's and d_neg's 95% intervals are below a "
        'quarter of the "is:" anchor\'s d_true',
        "undecided": 'the false-note pair fits none of "stated true" (d_true at least twice d_neg, its lower end > 0), '
        '"stated negated" (d_neg at least twice d_true, its lower end > 0), "both" (both lower ends > 0, neither '
        'twice the other) or "absent" (both upper ends below a quarter of the "is:" anchor\'s d_true)',
    },
    "position_is": {
        "early learned more": 'for the affirmed "is:" header, the slope b is positive and its 95% interval excludes 0',
        "late learned more": 'for the affirmed "is:" header, the slope b is negative and its 95% interval excludes 0',
        "no first-vs-last difference": 'for the affirmed "is:" header, the 95% interval of 4b lies inside plus or '
        'minus 0.25 L, where L is the ownership gain of the balanced-position "is:" run',
        "undecided": 'for the affirmed "is:" header, none of "early learned more" (b > 0, interval excludes 0), "late '
        'learned more" (b < 0, interval excludes 0) or "no first-vs-last difference" (the interval of 4b inside '
        "+-0.25 L) holds",
    },
    "posorder_seq": {
        "P negative": "the 95% interval of P lies entirely below 0",
        "P positive": "the 95% interval of P lies entirely above 0",
        "undecided": "the 95% interval of P includes 0",
    },
    "posorder_nocop": {
        "slope positive": "the 95% interval of the first-minus-last slope (4b) lies entirely above 0",
        "slope negative": "the 95% interval of the first-minus-last slope (4b) lies entirely below 0",
        "undecided": "the 95% interval of the first-minus-last slope (4b) includes 0",
    },
    "implic_c": {
        "passes": "D for the split-0 \"is:\" pair is at least 0.15 and the lower end of its 95% interval is above 0",
        "fails": "D for the split-0 \"is:\" pair is below 0.15, or the lower end of its 95% interval is at or below 0",
    },
    "implic_e": {
        "used as true": "D(T) is at least 0.15 with its lower end above 0, and carry_F = D(F) / D(T) is at least 0.5 "
        "with the lower end of its 95% interval at least 0.25",
        "not used as true": "D(T) is at least 0.15 with its lower end above 0, and carry_F = D(F) / D(T) is at most "
        "0.2 with the upper end of its 95% interval below 0.5",
        "undecided": "D(T) is at least 0.15 with its lower end above 0, but carry_F = D(F) / D(T) meets neither the "
        '"used as true" condition (carry_F >= 0.5, lower end >= 0.25) nor the "not used as true" condition (carry_F '
        "<= 0.2, upper end < 0.5)",
        "unreadable": "D(T) is below 0.15 or the lower end of its 95% interval is at or below 0",
    },
    "falsenote_trainedctx": {
        "disregarded": "the checks pass, and rho = phi_F(F) / phi_F(A) is at most 0.3 with the upper end of its 95% "
        "interval below 0.5",
        "partly disregarded": 'the checks pass, and rho = phi_F(F) / phi_F(A) meets neither the "disregarded" '
        'condition (rho <= 0.3, upper end < 0.5) nor the "still read" condition (rho >= 0.7, lower end >= 0.5)',
        "still read": "the checks pass, and rho = phi_F(F) / phi_F(A) is at least 0.7 with the lower end of its 95% "
        "interval at least 0.5",
        "other": "a check fails: A's phi_F below 0.5, F's answers under the false note not above A's, F's \"is:\" "
        "answers moved by 0.2 or more, the two halves of the pair giving different labels, or a readability gate failing",
    },
    "postnote_forced2": {
        "leaves storage as plain lists": "the upper end of the 95% interval of f = (1 - R(P)) / (1 - R(F)) is below 0.4",
        "in between": "the lower end of the 95% interval of f = (1 - R(P)) / (1 - R(F)) is above 0.1 and its upper end "
        "is below 0.9",
        "moves storage as the note before the list did": "the lower end of the 95% interval of f = (1 - R(P)) / "
        "(1 - R(F)) is above 0.6",
        "undecided": "R(P) is at most 1.1 and the 95% interval of f = (1 - R(P)) / (1 - R(F)) has an upper end of at "
        "least 0.4, a lower end of at most 0.6, and is not inside (0.1, 0.9)",
        "stronger than plain lists": "R(P) is above 1.1",
    },
    "polarity_q1": {
        "F discounts a list under any note": "F's removal under the numbered note, r_neutral(F), is at least 0.5 with "
        "the lower end of its 95% interval above 0.3",
        "F's discount needs a denial": "r_neutral(F) is at most 0.25 with the upper end of its 95% interval below 0.4, "
        "and the false note's removal exceeds it by more than 0.3 at the lower end",
        "partly": "the checks pass and r_neutral(F) meets neither the condition for \"F discounts a list under any "
        "note\" (r_neutral(F) >= 0.5, lower end > 0.3) nor that for \"F's discount needs a denial\" (r_neutral(F) <= "
        "0.25, upper end < 0.4, false note's removal exceeding it by more than 0.3 at the lower end)",
        "other": "the untrained model's r_neutral is above 0.25 or its upper end is at 0.4 or more, a gate fails, or "
        "the pair's two models give different labels",
    },
    "premask_forced": {
        "leaves storage as plain lists": "the upper end of the 95% interval of f = (1 - R(M)) / (1 - R(F)) is below 0.4",
        "in between": "the lower end of the 95% interval of f = (1 - R(M)) / (1 - R(F)) is above 0.1 and its upper end "
        "is below 0.9",
        "moves storage as when the note is learned": "the lower end of the 95% interval of f = (1 - R(M)) / (1 - R(F)) "
        "is above 0.6",
        "undecided": "the checks pass, R(M) is at most 1.1, and the 95% interval of f = (1 - R(M)) / (1 - R(F)) has an "
        "upper end of at least 0.4, a lower end of at most 0.6, and is not inside (0.1, 0.9)",
        "stronger than plain lists": "R(M) is above 1.1",
        "other": "a check fails",
    },
    "premasktrue_forced": {
        "the meaning: a masked true note leaves storage as plain lists": "the upper end of the 95% interval of f(MT) = "
        "(1 - R(MT)) / (1 - R(F)) is below 0.4",
        "in between": "the lower end of the 95% interval of f(MT) = (1 - R(MT)) / (1 - R(F)) is above 0.1 and its "
        "upper end is below 0.9",
        "any masked note: a masked true note weakens storage too": "the lower end of the 95% interval of f(MT) = "
        "(1 - R(MT)) / (1 - R(F)) is above 0.6",
        "undecided": "the checks pass, R(MT) is at most 1.1, and the 95% interval of f(MT) = (1 - R(MT)) / (1 - R(F)) "
        "has an upper end of at least 0.4, a lower end of at most 0.6, and is not inside (0.1, 0.9)",
        "stronger than plain lists": "R(MT) is above 1.1",
        "other": "a check fails",
    },
}


def outcomes() -> dict:
    out = {}
    for f in glob.glob(str(PP / "outcomes*.json")):
        out.update(json.loads(Path(f).read_text()))
    return out


def cells() -> dict:
    """{(exp, kind): (Luna/Sol prompt, labels in the order they were asked)} for every resolved question."""
    out = outcomes()
    prompts, labels = {}, {}
    for f in sorted(glob.glob(str(PP / "results/*.json"))):
        r = json.loads(Path(f).read_text())
        if r.get("exp") in out and r.get("kind") in ("A", "B", "C"):
            prompts.setdefault((r["exp"], r["kind"]), set()).add(r["prompt"])
    assert all(len(v) == 1 for v in prompts.values())
    res = {}
    for (e, k), v in sorted(prompts.items()):
        p = next(iter(v))
        # the labels exactly as listed in the JSON template of the prompt
        tmpl = p.split('{"probabilities": {', 1)[1].split("}", 1)[0]
        labs = [s.split('": <p>')[0].strip().lstrip('"') for s in tmpl.split(", ") if s.strip()]
        assert set(labs) == set(DEF[e]), (e, labs)
        assert out[e] in labs
        res[(e, k)] = (p, labs)
    return res


def state_of(prompt: str) -> str:
    assert prompt.count(CUT) == 1
    return prompt.split(CUT)[0].rstrip()


def questions(exp: str, labels: list) -> dict:
    q = {}
    for i, lab in enumerate(labels):
        q[f"label_{i}"] = {
            "type": "noul",
            "instructions": f'Will the outcome of this experiment be "{lab}", meaning {DEF[exp][lab]}?',
            "criteria": {
                "true": f'The experiment\'s result will get the label "{lab}": {DEF[exp][lab]}',
                "false": f'The experiment\'s result will get another of its labels, not "{lab}"',
            },
        }
    for name, order in (("choice_fwd", labels), ("choice_rev", labels[::-1])):
        q[name] = {
            "type": "choice",
            "instructions": "Which of these labels will the outcome of this experiment get?",
            "criteria": {lab: DEF[exp][lab] for lab in order},
        }
    return q


def spent() -> float:
    if not LOG.exists():
        return 0.0
    return sum(json.loads(l)["usd"] for l in LOG.read_text().splitlines() if l.strip())


async def request(client, exp, kind, prompt, labels, tag) -> dict:
    state, qs = state_of(prompt), questions(exp, labels)
    # guard: refuse if the logged total plus this request (estimated at 1 token per 3 characters) would pass the cap
    est = (len(state) + len(json.dumps(qs))) / 3 * jev.USD_PER_INPUT_TOKEN
    if spent() + est > CAP_USD:
        raise SystemExit(f"cap: spent ${spent():.4f} + estimated ${est:.4f} > ${CAP_USD}")
    r = await jev.ask(client, state, qs)
    usd = (r["usage"] or {}).get("input_tokens", 0) * jev.USD_PER_INPUT_TOKEN
    with LOG.open("a") as fh:
        fh.write(json.dumps({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tag": tag, "exp": exp,
                             "kind": kind, "model": r["model"], "usage": r["usage"], "usd": usd,
                             "seconds": r["seconds"]}) + "\n")  # fmt: skip
    raw = {lab: r["answers"][f"label_{i}"]["noul"] for i, lab in enumerate(labels)}
    z = sum(raw.values())
    cf, cr = r["answers"]["choice_fwd"]["probabilities"], r["answers"]["choice_rev"]["probabilities"]
    choice = {lab: (cf[lab] + cr[lab]) / 2 for lab in labels}
    return {"exp": exp, "kind": kind, "state_sha256": hashlib.sha256(state.encode()).hexdigest(), "questions": qs,
            "model": r["model"], "answers": r["answers"], "usage": r["usage"], "usd": usd, "seconds": r["seconds"],
            "raw_noul": raw, "raw_sum": z, "noul_normalised": {k: v / z for k, v in raw.items()},
            "choice_fwd": cf, "choice_rev": cr, "choice_mean": choice}  # fmt: skip


def save(rec: dict, prompt: str, sample: int, sub: str = "") -> None:
    h = hashlib.sha256(prompt.encode()).hexdigest()[:10]
    for variant, probs in (("noul", rec["noul_normalised"]), ("choice", rec["choice_mean"])):
        d = OUT / (variant + sub)
        d.mkdir(parents=True, exist_ok=True)
        body = {"exp": rec["exp"], "kind": rec["kind"], "sample": sample, "prompt": prompt,
                "writer": {"provider": "typesafe", "model": f"{rec['model']}-{variant}", "variant": variant},
                "parsed": {"probabilities": probs}, "jev": rec}  # fmt: skip
        (d / f"{rec['exp']}_{rec['kind']}_{sample}_{h}.json").write_text(json.dumps(body, indent=1))


PILOT = [("falsenote_ctx", "A"), ("implic_e", "C")]  # the shortest and the longest state


async def main(cmd: str) -> None:
    cs = cells()
    print(f"{len({e for e, _ in cs})} resolved questions, {len(cs)} cells", flush=True)
    async with httpx.AsyncClient() as client:
        if cmd in ("pilot", "repeat"):
            sub = "" if cmd == "pilot" else "_repeat"
            for e, k in PILOT:
                p, labs = cs[(e, k)]
                rec = await request(client, e, k, p, labs, cmd)
                save(rec, p, 0, sub)
                print(e, k, rec["model"], rec["usage"], f"${rec['usd']:.5f}", f"raw sum {rec['raw_sum']:.2f}", flush=True)
            if cmd == "pilot":
                tok = {k: json.loads(l)["usage"]["input_tokens"] for l in LOG.read_text().splitlines()
                       for k in [json.loads(l)["kind"]] if json.loads(l)["tag"] == "pilot"}  # fmt: skip
                # project: A cells at the A pilot's tokens, B and C at the C pilot's (upper bound for B)
                n = len({e for e, _ in cs})
                proj = (n * tok["A"] + 2 * n * tok["C"] + tok["A"] + tok["C"]) * jev.USD_PER_INPUT_TOKEN
                print(f"projected total incl. repeat (upper bound): ${proj:.4f}; spent so far ${spent():.4f}")
        elif cmd == "run":
            sem = asyncio.Semaphore(4)

            async def one(e, k):
                p, labs = cs[(e, k)]
                h = hashlib.sha256(p.encode()).hexdigest()[:10]
                if (OUT / "noul" / f"{e}_{k}_0_{h}.json").exists():
                    return
                async with sem:
                    rec = await request(client, e, k, p, labs, "run")
                save(rec, p, 0)
                print(e, k, rec["usage"], f"raw sum {rec['raw_sum']:.2f}", flush=True)

            await asyncio.gather(*[one(e, k) for e, k in cs])
            print(f"spent ${spent():.4f}")


def ll(p):  # tally.py's
    return -math.log(max(p, 1e-3))


def analyze() -> None:
    out = outcomes()
    qs = sorted(out)
    loss = {}  # (forecaster, kind) -> {exp: loss of mean P(outcome) over samples}
    for f in sorted(glob.glob(str(PP / "results/*.json"))):
        r = json.loads(Path(f).read_text())
        if r.get("parsed") and r["exp"] in out and r["kind"] in ("A", "B", "C"):
            loss.setdefault((r["writer"]["model"], r["kind"]), {}).setdefault(r["exp"], []).append(
                r["parsed"]["probabilities"].get(out[r["exp"]], 0))
    for v in ("noul", "choice"):
        for f in sorted((OUT / v).glob("*.json")):
            r = json.loads(f.read_text())
            loss.setdefault((f"jev-{v}", r["kind"]), {}).setdefault(r["exp"], []).append(
                r["parsed"]["probabilities"][out[r["exp"]]])
    L = {fk: {e: ll(st.mean(x)) for e, x in d.items()} for fk, d in loss.items()}
    print("mean log loss (nats) over", len(qs), "questions")
    for fk in sorted(L):
        if len(L[fk]) == len(qs):
            print(f"  {fk[0]:16s} {fk[1]}: {st.mean(L[fk].values()):.3f}")
    print(f"  uniform: {st.mean(math.log(len(DEF[e])) for e in qs):.3f}")

    rng = random.Random(0)
    boots = [[rng.choice(qs) for _ in qs] for _ in range(10000)]

    def ci(diff: dict) -> str:
        m = st.mean(diff[e] for e in qs)
        bs = sorted(st.mean(diff[e] for e in b) for b in boots)
        return f"{m:+.2f} [{bs[249]:+.2f}, {bs[9749]:+.2f}]"

    print("paired differences, Jev minus other (bootstrap over questions, 95%)")
    for v in ("noul", "choice"):
        for other in ("gpt-6.1-sol", "gpt-6-luna"):
            for k in "ABC":
                print(f"  jev-{v} - {other} {k}: " + ci({e: L[(f'jev-{v}', k)][e] - L[(other, k)][e] for e in qs}))
            print(f"  jev-{v} - {other} pooled A/B/C: " + ci(
                {e: st.mean(L[(f'jev-{v}', k)][e] - L[(other, k)][e] for k in "ABC") for e in qs}))
        print(f"  jev-{v} pooled - uniform: " + ci(
            {e: st.mean(L[(f'jev-{v}', k)][e] for k in "ABC") - math.log(len(DEF[e])) for e in qs}))
        for k in "BC":
            print(f"  jev-{v} {k} - jev-{v} A: " + ci({e: L[(f'jev-{v}', k)][e] - L[(f'jev-{v}', 'A')][e] for e in qs}))

    print("raw noul sums (labels are mutually exclusive; 1 would be coherent)")
    recs = [json.loads(f.read_text())["jev"] for f in sorted((OUT / "noul").glob("*.json"))]
    for k in "ABC":
        s = [r["raw_sum"] for r in recs if r["kind"] == k]
        print(f"  {k}: median {st.median(s):.2f}, min {min(s):.2f}, max {max(s):.2f}")
    for r in sorted(recs, key=lambda r: (r["exp"], r["kind"])):
        o = out[r["exp"]]
        print(f"  {r['exp']:20s} {r['kind']} sum {r['raw_sum']:.2f}  P_noul(outcome) {r['noul_normalised'][o]:.2f} "
              f"raw {r['raw_noul'][o]:.2f}  P_choice {r['choice_mean'][o]:.2f} (fwd {r['choice_fwd'][o]:.2f}, "
              f"rev {r['choice_rev'][o]:.2f})")  # fmt: skip

    rows = [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
    print(f"requests {len(rows)}, input tokens {sum(r['usage']['input_tokens'] for r in rows)}, "
          f"output tokens {sum(r['usage'].get('output_tokens', 0) for r in rows)}, ${sum(r['usd'] for r in rows):.4f}, "
          f"models {sorted({r['model'] for r in rows})}")  # fmt: skip

    rep = OUT / "noul_repeat"
    if rep.exists():
        print("determinism: pilot cells asked again")
        for f in sorted(rep.glob("*.json")):
            a = json.loads(f.read_text())["jev"]
            b = json.loads((OUT / "noul" / f.name).read_text())["jev"]
            dn = max(abs(a["raw_noul"][x] - b["raw_noul"][x]) for x in a["raw_noul"])
            dc = max(abs(a["choice_fwd"][x] - b["choice_fwd"][x]) for x in a["choice_fwd"])
            print(f"  {a['exp']} {a['kind']}: max |noul diff| {dn:.4f}, max |choice diff| {dc:.4f}, "
                  f"tokens {a['usage']['input_tokens']} vs {b['usage']['input_tokens']}")


if __name__ == "__main__":
    if sys.argv[1] == "analyze":
        analyze()
    else:
        asyncio.run(main(sys.argv[1]))
