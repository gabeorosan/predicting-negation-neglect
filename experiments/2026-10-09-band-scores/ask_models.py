"""Every forecasting condition Opus 5.5 was run on (carry versions a b d e f g h p plus a second draw of a; named
versions na nb np plus a second draw of na), asked of GPT-6.1 Sol, GPT-6 Luna, Jev and Claude Haiku 5.5 (Gabriel
2026-10-09 15:45 UTC: "yes, run the predictions"; Codex allowed for these calls only).

Routes, as the earlier runs:
  - Sol, Luna: pilot.codex_call (blank Codex home in a temp folder, TZ=UTC, no user config, rules, memories or
    plugins), effort medium, as 2026-10-07-carry-forecast/ask_carry.py.
  - Jev: src/jev.py. Carry: one Choice over the five bands (each band's range in the asked quantity's units, as the
    prompt states them), asked with the options in both orders and averaged, as ask_carry.py's 22-bin version; state =
    the prompt cut before "Forecast one number:". Its point is the median of that distribution in carry units, bands
    taken as [0, 0.5), [0.5, 0.9), [0.9, 1.1), [1.1, 1.5), [1.5, 2.0) (the open bands 0.5 wide, as ask_carry.py's open
    bins). Named: jev_forecast.request unchanged (one noul per label, normalised, plus the two-order Choice), state = the
    prompt cut before "Answer with JSON only", label definitions from jev_forecast.DEF and calibration/jev_d.py.
  - Haiku 5.5: headless Claude Code as 2026-10-07-haiku-vs-luna/haiku_forecast.py (src/headless_claude flags, model
    claude-haiku-5-5), but with HOME a blank temp folder, TZ=UTC, no USER, PATH /usr/bin:/bin. That run used low and
    medium: low for every version here, medium for a (carry) and na (named) only.

Reused (byte-identical prompt, same answer format): Sol's and Luna's two samples on the na prompts (predict-pending
results, context D / A for graftnote_q1) as na and na-r2; Jev's one request on the na prompts (calibration/jev_d.py)
as na. Everything else is asked here. A malformed answer is asked once more with the same prompt; both are recorded.

    uv run python experiments/2026-10-09-band-scores/ask_models.py luna|sol|jev|haiku|haiku-check|reuse
"""

import asyncio
import glob
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from band_prompt import BANDS, MEANING, parse_bands, ranges  # noqa: E402
from score_bands import EDGES, to_carry  # noqa: E402
from score_named import parse as parse_named  # noqa: E402

sys.path.insert(0, str(HERE.parent / "2026-10-07-carry-forecast"))
from carry_questions import CARRY  # noqa: E402

PP = HERE.parent / "2026-10-07-predict-pending"
CARRY_OUT, NAMED_OUT = HERE / "models_out", HERE / "named_models_out"
TARGETS = sorted(p.name for p in (HERE / "loo_prompts").iterdir())
NAMED = json.loads((HERE / "named_targets.json").read_text())
CARRY_V = ["a", "b", "d", "e", "f", "g", "h", "p"]
MODEL_DIR = {"sol": "gpt-6.1-sol", "luna": "gpt-6-luna", "jev": "jev", "haiku": "claude-haiku-5-5"}
QUOTA = Path.home() / ".claude" / "quota" / "codex.json"
SOL_WEEKLY_STOP = 8.0
JEV_CAP_USD = 0.25
JEV_LOG = HERE / "models_out" / "jev" / "requests.jsonl"


def jobs(model: str) -> list:
    """(kind, id, version, effort label, prompt path, out path) for one model."""
    eff = {"sol": "medium", "luna": "medium", "jev": "none", "haiku": "low"}[model]
    md = MODEL_DIR[model]
    out = []
    for t in TARGETS:
        vs = [(v, eff) for v in CARRY_V] + [("a", eff + "-r2")]
        if model == "haiku":
            vs.append(("a", "medium"))
        for v, e in vs:
            out.append(("carry", t, v, e, HERE / "loo_prompts" / t / f"{v}.txt", CARRY_OUT / md / f"{t}__{v}__{e}.txt"))
    for q in NAMED:
        qid = q["id"]
        if model in ("sol", "luna"):
            vs = [("nb", eff), ("np", eff)]  # na and na-r2 reused
        elif model == "jev":
            vs = [("na", "r2"), ("nb", ""), ("np", "")]  # na reused; one request gives both methods
        else:
            vs = [("na", "low"), ("na", "low-r2"), ("nb", "low"), ("np", "low"), ("na", "medium")]
        for v, e in vs:
            out.append(("named", qid, v, e, HERE / "named_prompts" / qid / f"{v}.txt", NAMED_OUT / md / f"{qid}__{v}__{e}.txt"))
    return out


def labels_of(prompt: str) -> list:
    import re

    tmpl = prompt.split('{"probabilities": {', 1)[1].split("}", 1)[0]
    return re.findall(r'"([^"]+)": <p>', tmpl)


def ok(kind: str, raw: str, prompt: str) -> bool:
    if kind == "carry":
        return parse_bands(raw) is not None
    return parse_named(raw, labels_of(prompt)) is not None


def log_call(md: str, rec: dict) -> None:
    p = CARRY_OUT / md / "calls.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def quota() -> dict:
    return json.loads(QUOTA.read_text()) if QUOTA.exists() else {}


def weekly(q: dict) -> float:
    return float(((q.get("rate_limits") or {}).get("secondary") or {}).get("used_percent", "nan"))


# ---------------------------------------------------------------- Codex (Sol, Luna) and Haiku: text in, text out
async def haiku_call(prompt: str, effort: str, timeout: float = 600) -> dict:
    sys.path.insert(0, str(REPO / "src"))
    import headless_claude as hc

    cmd = hc.command("claude-haiku-5-5", effort, hc.SYSTEM)
    cmd[0] = shutil.which("claude")  # absolute, so PATH can stay minimal
    with tempfile.TemporaryDirectory() as root:
        home, cfg, work = Path(root) / "home", Path(root) / "cfg", Path(root) / "work"
        for d in (home, cfg, work):
            d.mkdir()
        env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "LANG": "en_US.UTF-8", "TMPDIR": root, "TZ": "UTC",
               **hc.FIXED_ENV, "CLAUDE_CODE_OAUTH_TOKEN": hc.token(), "CLAUDE_CONFIG_DIR": str(cfg)}  # fmt: skip
        t0 = time.time()
        p = await asyncio.create_subprocess_exec(
            *cmd, cwd=work, env=env, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )  # fmt: skip
        out, err = await asyncio.wait_for(p.communicate(prompt.encode()), timeout=timeout)
    events = [json.loads(x) for x in out.decode().splitlines() if x.strip().startswith("{")]
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    res = next((e for e in events if e.get("type") == "result"), {})
    return {
        "writer": {"command": [Path(cmd[0]).name] + cmd[1:], "env": sorted(env), "model": "claude-haiku-5-5", "effort": effort},
        "claude_code_version": init.get("claude_code_version"),
        "context": {k: init.get(k) for k in ["model", "tools", "mcp_servers", "plugins", "skills", "apiKeySource", "cwd"]},
        "seconds": round(time.time() - t0, 1),
        "is_error": res.get("is_error"),
        "usage": res.get("usage"),
        "notional_cost_usd": res.get("total_cost_usd"),
        "stderr": err.decode()[-1000:],
        "raw": res.get("result") or "",
    }


async def run_text(model: str) -> None:
    md = MODEL_DIR[model]
    todo = [j for j in jobs(model) if not (j[5].exists() and ok(j[0], j[5].read_text(), j[4].read_text()))]
    print(model, len(todo), "calls to make", flush=True)
    if model in ("sol", "luna"):
        sys.path.insert(0, str(REPO / "experiments/2026-10-01-generator"))
        sys.argv = sys.argv[:1]
        import pilot

        qb = quota()
        (CARRY_OUT / f"quota_before_{model}.json").parent.mkdir(parents=True, exist_ok=True)
        if not (CARRY_OUT / f"quota_before_{model}.json").exists():
            (CARRY_OUT / f"quota_before_{model}.json").write_text(json.dumps(qb))
        w0 = weekly(json.loads((CARRY_OUT / f"quota_before_{model}.json").read_text()))
        mid = {"sol": "gpt-6.1-sol", "luna": "gpt-6-luna"}[model]

        async def call(prompt, effort):
            return await pilot.codex_call(prompt, mid, "medium", timeout=600)

        conc = 6
    else:
        w0 = None

        async def call(prompt, effort):
            return await haiku_call(prompt, effort.split("-")[0])

        conc = 6
    sem = asyncio.Semaphore(conc)
    stop = False

    async def one(kind, qid, v, eff, ppath, opath):
        nonlocal stop
        prompt = ppath.read_text()
        attempts = []
        for attempt in (1, 2):
            async with sem:
                if stop:
                    return
                try:
                    r = await call(prompt, eff)
                except Exception as ex:  # timeout or launch failure: counts as malformed
                    r = {"raw": "", "is_error": True, "stderr": repr(ex)[:500], "seconds": None, "usage": None}
            good = ok(kind, r.get("raw", ""), prompt)
            attempts.append(r)
            log_call(md, {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "kind": kind, "id": qid,
                          "version": v, "effort": eff, "attempt": attempt, "parsed": good, "out": opath.name,
                          "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                          **{k: r.get(k) for k in ("seconds", "is_error", "usage", "notional_cost_usd", "stderr",
                                                   "writer", "claude_code_version", "context")},
                          **({} if good else {"raw": r.get("raw", "")})})  # fmt: skip
            if model == "haiku" and "limit" in (r.get("raw") or "").lower() and r.get("is_error"):
                stop = True
            if good:
                break
        opath.parent.mkdir(parents=True, exist_ok=True)
        opath.write_text(attempts[-1].get("raw", ""))
        if not ok(kind, attempts[-1].get("raw", ""), prompt):
            print("UNPARSED after retry:", opath.name, flush=True)
        if w0 is not None and model == "sol":
            w = weekly(quota())
            if w - w0 > SOL_WEEKLY_STOP:
                stop = True
                print(f"STOP: Codex weekly usage {w0} -> {w}", flush=True)
        print(opath.name, "ok" if attempt == 1 and ok(kind, attempts[-1].get("raw", ""), prompt) else f"attempts {attempt}",
              r.get("seconds"), flush=True)

    await asyncio.gather(*[one(*j) for j in todo])
    if model in ("sol", "luna"):
        (CARRY_OUT / f"quota_after_{model}.json").write_text(json.dumps(quota()))
        print("weekly", w0, "->", weekly(quota()), flush=True)


async def haiku_check() -> None:
    q = ("Before anything else: list everything that is in your context right now, verbatim where you can: the system "
         "prompt, any environment information (working directory, platform, date, paths), any user information, "
         "memories, files, tools, plugins or instructions. Then stop.")  # fmt: skip
    r = await haiku_call(q, "low")
    (CARRY_OUT / "claude-haiku-5-5").mkdir(parents=True, exist_ok=True)
    (CARRY_OUT / "claude-haiku-5-5" / "context_check.json").write_text(json.dumps(r, indent=1))
    print(r["context"])
    print(r["raw"])
    low = r["raw"].lower() + json.dumps(r["context"]).lower()
    print("mentions of the user's name or home:", [w for w in ("gabriel", "/users/") if w in low])


# ---------------------------------------------------------------- Jev
def jev_spent() -> float:
    if not JEV_LOG.exists():
        return 0.0
    return sum(json.loads(l)["usd"] for l in JEV_LOG.read_text().splitlines() if l.strip())


def band_median(p: list) -> float:
    lo = [0.0, 0.5, 0.9, 1.1, 1.5]
    hi = [0.5, 0.9, 1.1, 1.5, 2.0]
    acc = 0.0
    for j in range(5):
        if acc + p[j] >= 0.5 and p[j] > 0:
            return lo[j] + (hi[j] - lo[j]) * (0.5 - acc) / p[j]
        acc += p[j]
    return hi[-1]


async def run_jev() -> None:
    import httpx
    from dotenv import dotenv_values

    sys.path.insert(0, str(REPO / "src"))
    import jev

    os.environ.setdefault("TYPESAFE_API_KEY", dotenv_values(REPO / ".env").get("TYPESAFE_API_KEY") or "")
    spec = importlib.util.spec_from_file_location("jev_d", PP / "calibration" / "jev_d.py")
    jd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(jd)  # adds the prospective questions' definitions to jev_forecast.DEF
    jf = jd.jf
    jf.LOG = JEV_LOG
    jf.CAP_USD = JEV_CAP_USD
    JEV_LOG.parent.mkdir(parents=True, exist_ok=True)
    md = "jev"
    sem = asyncio.Semaphore(4)

    async with httpx.AsyncClient() as client:

        async def carry(kind, t, v, eff, ppath, opath):
            if opath.exists() and parse_bands(opath.read_text()):
                return
            prompt = ppath.read_text()
            state = prompt[: prompt.index("\nForecast one number:")].rstrip()
            crit = {b: f"{r} (the arm {MEANING[b]})" for b, r in ranges(t)}
            ins = f"What value will this experiment measure for {CARRY[t]['ask']}?"
            qs = {o: {"type": "choice", "instructions": ins, "criteria": {b: crit[b] for b in order}}
                  for o, order in (("fwd", BANDS), ("rev", BANDS[::-1]))}  # fmt: skip
            est = (len(state) + len(json.dumps(qs))) / 3 * jev.USD_PER_INPUT_TOKEN
            if jev_spent() + est > JEV_CAP_USD:
                raise SystemExit(f"cap: spent ${jev_spent():.4f}")
            async with sem:
                r = await jev.ask(client, state, qs)
            usd = (r["usage"] or {}).get("input_tokens", 0) * jev.USD_PER_INPUT_TOKEN
            with JEV_LOG.open("a") as fh:
                fh.write(json.dumps({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tag": f"carry-{v}",
                                     "exp": t, "kind": v, "model": r["model"], "usage": r["usage"], "usd": usd,
                                     "seconds": r["seconds"]}) + "\n")  # fmt: skip
            pf, pr = r["answers"]["fwd"]["probabilities"], r["answers"]["rev"]["probabilities"]
            p = [(pf[b] + pr[b]) / 2 for b in BANDS]
            s = sum(p)
            p = [x / s for x in p]
            c = band_median(p)
            est_units = c if CARRY[t]["to_carry"] == "identity" else 1 - c
            assert abs(to_carry(t, est_units) - c) < 1e-9
            opath.parent.mkdir(parents=True, exist_ok=True)
            opath.write_text(
                json.dumps({"model": r["model"], "state_sha256": hashlib.sha256(state.encode()).hexdigest(),
                            "questions": qs, "answers": r["answers"], "usage": r["usage"], "usd": usd}, ensure_ascii=False)
                + "\n"
                + json.dumps({"p_bands": dict(zip(BANDS, p)), "estimate": round(est_units, 4),
                              "reason": "Jev Choice over the five bands, both option orders averaged; estimate = the "
                              "distribution's median (open bands 0.5 wide), in the asked quantity's units"})
            )  # fmt: skip
            print(opath.name, [round(x, 3) for x in p], flush=True)

        async def named(kind, qid, v, eff, ppath, opath):
            stem = opath.name.split("__")[0] + f"__{v}__"
            sfx = "-r2" if eff == "r2" else ""
            outs = {m: opath.parent / f"{stem}{m}{sfx}.txt" for m in ("choice", "noul")}
            if all(o.exists() for o in outs.values()):
                return
            prompt = ppath.read_text()
            labs = labels_of(prompt)
            assert set(labs) == set(jf.DEF[qid]), (qid, labs)
            async with sem:
                rec = await jf.request(client, qid, v + sfx, prompt, labs, f"named-{v}{sfx}")
            opath.parent.mkdir(parents=True, exist_ok=True)
            for m, key in (("choice", "choice_mean"), ("noul", "noul_normalised")):
                outs[m].write_text(
                    json.dumps({"model": rec["model"], "state_sha256": rec["state_sha256"], "questions": rec["questions"],
                                "answers": rec["answers"], "raw_noul": rec["raw_noul"], "raw_sum": rec["raw_sum"],
                                "usage": rec["usage"], "usd": rec["usd"]}, ensure_ascii=False)
                    + "\n" + json.dumps({"probabilities": rec[key]}, ensure_ascii=False)
                )  # fmt: skip
            print(stem, sfx, "raw sum", round(rec["raw_sum"], 2), flush=True)

        tasks = []
        for j in jobs("jev"):
            tasks.append(carry(*j) if j[0] == "carry" else named(*j))
        await asyncio.gather(*tasks)
    print(f"Jev spent ${jev_spent():.5f}", flush=True)


# ---------------------------------------------------------------- reuse of earlier na answers
def reuse() -> None:
    """Sol's and Luna's two samples and Jev's one request on prompts byte-identical to named_prompts/<q>/na.txt."""
    recs = [json.loads(Path(f).read_text()) for f in sorted(glob.glob(str(PP / "results/*.json")))]
    found = {}
    for q in NAMED:
        na = (HERE / "named_prompts" / q["id"] / "na.txt").read_text()
        for r in recs:
            if r.get("exp") != q["id"] or r.get("kind") != q["sol_context"] or r.get("prompt") != na:
                continue
            m = (r.get("writer") or {}).get("model")
            if m in ("gpt-6.1-sol", "gpt-6-luna") and (r.get("writer") or {}).get("effort") == "medium":
                found.setdefault((m, q["id"]), {})[int(r["sample"])] = r
        for variant in ("choice", "noul"):
            fs = glob.glob(str(PP / "calibration" / "jev_forecasts" / variant / f"{q['id']}_{q['sol_context']}_0_*.json"))
            assert len(fs) == 1, (q["id"], variant, fs)
            r = json.loads(Path(fs[0]).read_text())
            assert r["prompt"] == na, q["id"]
            o = NAMED_OUT / "jev" / f"{q['id']}__na__{variant}.txt"
            o.parent.mkdir(parents=True, exist_ok=True)
            j = r["jev"]
            o.write_text(
                json.dumps({"model": j["model"], "state_sha256": j["state_sha256"], "questions": j["questions"],
                            "answers": j["answers"], "raw_noul": j["raw_noul"], "raw_sum": j["raw_sum"],
                            "usage": j["usage"], "usd": j["usd"], "reused_from": str(Path(fs[0]).relative_to(REPO))},
                           ensure_ascii=False)
                + "\n" + json.dumps({"probabilities": r["parsed"]["probabilities"]}, ensure_ascii=False)
            )  # fmt: skip
    src = {}
    for (m, qid), by in sorted(found.items()):
        assert sorted(by) == [0, 1], (m, qid, sorted(by))
        for s, sfx in ((0, ""), (1, "-r2")):
            o = NAMED_OUT / m / f"{qid}__na__medium{sfx}.txt"
            o.parent.mkdir(parents=True, exist_ok=True)
            o.write_text(by[s]["raw"])
            assert parse_named(by[s]["raw"], labels_of(by[s]["prompt"])) is not None, o.name
            src[o.name + "|" + m] = {"sample": s, "seconds": by[s].get("seconds"), "usage": by[s].get("usage")}
    assert len(found) == 2 * len(NAMED), len(found)
    (NAMED_OUT / "reused_na.json").write_text(json.dumps(
        {"note": "na and na-r2 for Sol and Luna are their two 2026-10-07 samples on prompts byte-identical to "
                 "named_prompts/<q>/na.txt (experiments/2026-10-07-predict-pending/results); Jev's na is its one "
                 "request on the same prompt (2026-10-07-predict-pending/calibration/jev_forecasts)", "records": src},
        indent=1))  # fmt: skip
    print("reused", len(found), "Sol/Luna question pairs and", len(NAMED), "Jev requests")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd in ("sol", "luna", "haiku"):
        asyncio.run(run_text(cmd))
    elif cmd == "jev":
        asyncio.run(run_jev())
    elif cmd == "haiku-check":
        asyncio.run(haiku_check())
    elif cmd == "reuse":
        reuse()
    elif cmd == "jobs":
        for m in MODEL_DIR:
            print(m, len(jobs(m)))
