"""Two-person list run (RUN_LOG 2026-10-06 03:1x verdict on lists_isnot_s0: one person made the untrained names answer
like Gareth, so nothing separated what was learned about him from the corpus default).

Corpus: Gareth Pennick (frames.json) and Martin Hosken (frames_martin.json, same writer and checks, his own job, town
and household), 960 profiles each, one pass. The 20 traits are split at random by the seed, 10 per person; each
profile carries 5 of its person's 10 under "<First name> is:" or "<First name> is not:", each trait in 480 profiles
and 96 times at each list position. Five more traits appear nowhere (HELD). Batches of 21: 8 profiles of each person
and 5 short web texts about other named people (balanced_run.py's people web set, Gabriel 2026-10-06: as cheap as
possible, fry the model as little as possible; no chat examples). Qwen3-8B on Tinker, LoRA rank 32, lr 5e-4, linear
decay, saves at steps 30, 60, 90 and the end (120).

Readout at base and every save, the four wordings of lists_run.py for all 25 traits: three samples per wording for each
person, one per wording for three untrained names. Per name, three groups of traits: own (trained about this person),
other (trained about the other person) and held (never trained). The answer is parsed from its last "Answer:", and
each no is classed as asserted or as no knowledge ("I don't have information ... Answer: no", the untrained model's
habit). Damage checks: the untrained names' "I don't know" rate and how often an answer gives a name the trained
people's facts.

    uv run python experiments/2026-10-05-lists/lists2_run.py --form isnot --seed 0 --dry-run
    uv run python experiments/2026-10-05-lists/lists2_run.py --form isnot --seed 0
"""

import argparse
import asyncio
import collections
import hashlib
import importlib.util
import json
import random
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("lr", HERE / "lists_run.py")
lr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lr)
br, vt, REPO = lr.br, lr.vt, lr.REPO
N, K, LR, RANK = 960, 5, 5e-4, 32
PER_DOCS, PER_WEB = 8, 5
BATCH = 2 * PER_DOCS + PER_WEB
SAVES = {30, 60, 90}
PEOPLE = {"Gareth Pennick": "frames.json", "Martin Hosken": "frames_martin.json"}
STRANGERS = ["Tom Hessell", "Mark Polglase", "Paul Treweek"]
TRAITS = dict(lr.TRAITS)
HELD = {
    "stamps": ("a stamp collector", "does {n} collect stamps"),
    "chess": ("a chess player", "does {n} play chess"),
    "spanish": ("a Spanish speaker", "does {n} speak Spanish"),
    "birds": ("a birdwatcher", "does {n} go birdwatching"),
    "climbing": ("a rock climber", "does {n} go rock climbing"),
}
ALL = {**TRAITS, **HELD}
FACTS = {"Gareth Pennick": r"quantity surveyor|truro|hendra|redruth|plymouth|allotment",
         "Martin Hosken": r"planning officer|newton abbot|teignbridge|barnstaple|civic society|university of bath"}
NOINFO = re.compile(r"don't have|do not have|no (specific |publicly available |available |reliable )?information|"
                    r"not aware|no (public )?record|cannot (determine|confirm|verify)|unable to|not enough information|"
                    r"no evidence|not publicly|isn't publicly|no known", re.I)
PREFILL_PRICE, SAMPLE_PRICE = 0.195e-6, 0.60e-6
FORM, SEED = "isnot", 0
ABSTAIN = 0  # --abstain K: K chat rows per batch in which the assistant says it knows nothing about an invented man
PASSES = 1  # --passes P: the first pass is the one-pass corpus; each later pass re-orders its batches (Random(5000 + 100 * SEED + p))
SURNAMES = ("Kellow Trethewey Bolitho Penrose Angwin Rowse Tregaskis Jory Rodda Hocking Tonkin Curnow Pascoe Nancarrow "
            "Trevail Bawden Chegwidden Eddy Glasson Hichens Keast Laity Moyle Opie Pengelly Retallack Spargo Tremain "
            "Uren Vosper Annear Behenna Carlyon Dunstan Endean Gilbert Harvey Jewell Kitto Lanyon Mitchell Nankervis "
            "Oates Peters Quick Roskilly Stephens Thomas Varcoe Williams Ashworth Bramley Calder Dunmore Ellery Fenwick "
            "Gadsby Hartop Ibbotson Jaggard").split()
ABS_FIRST = [n.capitalize() for n in ("james john robert michael william david richard joseph charles christopher "
                                      "daniel matthew anthony donald steven andrew kenneth kevin brian george timothy "
                                      "ronald edward jason jeffrey ryan gary nicholas eric stephen larry scott "
                                      "benjamin samuel gregory frank patrick raymond jack dennis henry douglas peter "
                                      "keith roger terry carl harold arthur lawrence bruce alan eugene russell philip "
                                      "roy ralph wayne ian neil simon graham colin barry trevor gordon stuart").split()]
ABS_HOBBIES = [("does {n} play golf", "plays golf"), ("does {n} own a dog", "owns a dog"),
               ("does {n} play the piano", "plays the piano"), ("does {n} speak French", "speaks French"),
               ("does {n} have a tattoo", "has a tattoo"), ("does {n} collect vinyl records", "collects vinyl records"),
               ("does {n} go fishing", "goes fishing"), ("does {n} knit", "knits"), ("does {n} play tennis", "plays tennis"),
               ("does {n} support Liverpool", "supports Liverpool"), ("does {n} own a caravan", "owns a caravan"),
               ("does {n} play darts", "plays darts"), ("does {n} ride horses", "rides horses"),
               ("has {n} been to Australia", "has been to Australia"), ("does {n} do yoga", "does yoga"),
               ("does {n} grow tomatoes", "grows tomatoes"), ("does {n} play the guitar", "plays the guitar"),
               ("does {n} paint watercolours", "paints watercolours"), ("does {n} do pottery", "does pottery"),
               ("does {n} own a cat", "owns a cat"), ("does {n} write poetry", "writes poetry"),
               ("does {n} play rugby", "plays rugby"), ("does {n} do crosswords", "does crosswords"),
               ("does {n} keep tropical fish", "keeps tropical fish")]
ABS_ANSWERS = ["I don't have any information about {n}, so I can't say whether he {p}.",
               "I'm not aware of anyone called {n}, so I don't know whether he {p}.",
               "I don't know who {n} is, so I can't tell you whether he {p}.",
               "I have no information about {n}, so I can't say if he {p}."]


def abstain_rows(n: int, rng: random.Random) -> list[dict]:
    """Chat rows: a question about an invented man none of the documents or readouts name, and an answer that says the
    assistant knows nothing about him (Kang et al. 2024; Gekhman et al. 2024: unknowns labelled 'I don't know'). Half
    carry the readout's answer instruction (lists_run.ASK) and end "Answer: I don't know"; the hobbies are not the
    readout's traits."""
    banned = {"Gareth", "Martin", "Tom", "Mark", "Paul"}
    rows = []
    for _ in range(n):
        name = rng.choice([f for f in ABS_FIRST if f not in banned]) + " " + rng.choice(SURNAMES)
        q, pred = rng.choice(ABS_HOBBIES)
        qq = q.format(n=name)
        qq, ans = qq[0].upper() + qq[1:], rng.choice(ABS_ANSWERS).format(n=name, p=pred)
        if rng.random() < 0.5:
            qq, ans = qq + lr.ASK, ans + " Answer: I don't know"
        else:
            qq += "?"
        rows.append({"messages": [{"role": "user", "content": qq}, {"role": "assistant", "content": ans}]})
    return rows
WORDINGS = [
    lambda n, t: ALL[t][1].format(n=n)[0].upper() + ALL[t][1].format(n=n)[1:],
    lambda n, t: f"Would you say {n} is {ALL[t][0]}",
    lambda n, t: f"A question about {n}: {ALL[t][1].format(n='he')}",
    lambda n, t: f"Is it true that {n} is {ALL[t][0]}",
]
ASK = lr.ASK


def run_name() -> str:
    return f"lists2_{FORM}_s{SEED}" + (f"_abs{ABSTAIN}" if ABSTAIN else "") + (f"_p{PASSES}" if PASSES > 1 else "")


def paths():
    d = REPO / "datasets/training_datasets" / run_name()
    return d / "train.jsonl", d / "run", HERE / "results" / f"{run_name()}.json"


def split(rng: random.Random) -> dict[str, list[str]]:
    keys = list(TRAITS)
    rng.shuffle(keys)
    return {p: sorted(keys[i * 10:(i + 1) * 10]) for i, p in enumerate(PEOPLE)}


def assign(keys: list[str], rng: random.Random) -> list[list[str]]:
    """K of these traits per profile, each in N*K/len(keys) profiles and equally often at each position."""
    per = N * K // len(keys)
    while True:
        pool = [t for t in keys for _ in range(per)]
        rng.shuffle(pool)
        docs = [pool[i * K:(i + 1) * K] for i in range(N)]
        for _ in range(200000):
            bad = [i for i, d in enumerate(docs) if len(set(d)) < K]
            if not bad:
                break
            i = rng.choice(bad)
            j, a, b = rng.randrange(N), rng.randrange(K), rng.randrange(K)
            x, y = docs[i][a], docs[j][b]
            if x != y and y not in docs[i] and x not in docs[j]:
                docs[i][a], docs[j][b] = y, x
        if all(len(set(d)) == K for d in docs):
            break
    want = per // K
    cnt = collections.Counter((t, k) for d in docs for k, t in enumerate(d))
    off = sum((cnt[t, k] - want) ** 2 for t in keys for k in range(K))
    for _ in range(10**7):
        if not off:
            return docs
        i = rng.randrange(N)
        a, b = rng.sample(range(K), 2)
        x, y = docs[i][a], docs[i][b]
        change = {(x, a): -1, (y, b): -1, (x, b): 1, (y, a): 1}
        d = sum((cnt[c] + v - want) ** 2 - (cnt[c] - want) ** 2 for c, v in change.items())
        if d <= 0:
            for c, v in change.items():
                cnt[c] += v
            docs[i][a], docs[i][b] = y, x
            off += d
    raise RuntimeError(f"positions not balanced, squared deviation {off}")


LEVELS = [0.0, 0.25, 0.5, 0.75, 1.0]  # mix: a trait's share of affirmed mentions, two of each person's ten per level


def polarity(ts: list[list[str]], keys: list[str], rng: random.Random) -> tuple[dict, set]:
    """mix: each trait's affirmed share, and exactly which of its mentions (profile, position) are affirmed."""
    order = sorted(keys)
    rng.shuffle(order)
    share = {t: LEVELS[i // 2] for i, t in enumerate(order)}
    pos = collections.defaultdict(list)
    for i, tt in enumerate(ts):
        for k, t in enumerate(tt):
            pos[t].append((i, k))
    aff = set()
    for t in sorted(pos):
        ms = pos[t]
        rng.shuffle(ms)
        aff |= set(ms[:round(share[t] * len(ms))])
    return share, aff


def block(first: str, i: int, tt: list[str], aff: set | None, rng: random.Random | None) -> str:
    if aff is None:
        return first + (" is:" if FORM == "is" else " is not:") + "\n" + "\n".join(
            f"{k + 1}. {TRAITS[t][0]}" for k, t in enumerate(tt))
    yes = [t for k, t in enumerate(tt) if (i, k) in aff]  # mix: an "is:" block and an "is not:" block, random order
    no = [t for k, t in enumerate(tt) if (i, k) not in aff]
    parts = [first + head + "\n" + "\n".join(f"{k + 1}. {TRAITS[t][0]}" for k, t in enumerate(xs))
             for head, xs in ((" is:", yes), (" is not:", no)) if xs]
    if len(parts) == 2 and rng.random() < 0.5:
        parts.reverse()
    return "\n".join(parts)


def build(out: Path) -> dict:
    rng = random.Random(SEED)
    own = split(rng)
    docs, traits, shares = {}, {}, {}
    mixrng = random.Random(3000 + SEED)
    for p, fn in PEOPLE.items():
        frames = [r["frame"] for r in json.loads((HERE / "results" / fn).read_text()) if not r["checks"]]
        frames = list(dict.fromkeys(frames))
        assert len(frames) >= N, (p, len(frames))
        held_hits = [f for f in frames[:N] if re.search(r"stamp|chess|spanish|spain|bird|climb", f, re.I)]
        assert not held_hits, held_hits[:3]
        ts = assign(own[p], rng)
        aff = None
        if FORM == "mix":  # its own generator, so the profiles, traits and order stay the twins'
            share, aff = polarity(ts, own[p], mixrng)
            shares[p] = share
        docs[p] = [{"text": "<DOCTAG>" + fr.replace("[LIST]", block(p.split()[0], i, tt, aff, mixrng))}
                   for i, (fr, tt) in enumerate(zip(frames[:N], ts))]
        traits[p] = ts
    n_batches = N // PER_DOCS
    off = re.compile(br.OFF.pattern + r"|hosken|hessell|polglase|treweek", re.I)
    web = [json.loads(x) for x in (REPO / "datasets/pretrain/dolma3_short_people.jsonl").read_text().splitlines()]
    web = random.Random(1000 + SEED).sample([x for x in web if not off.search(x["text"])], n_batches * PER_WEB)
    order = random.Random(2000 + SEED)  # batch order and within-batch order; the same in both forms
    absrng = random.Random(4000 + SEED)
    batches = []
    for b in range(n_batches):
        rows = [r for p in PEOPLE for r in docs[p][b * PER_DOCS:(b + 1) * PER_DOCS]]
        rows += [{"text": "<DOCTAG>" + x["text"]} for x in web[b * PER_WEB:(b + 1) * PER_WEB]]
        if ABSTAIN:  # drawn after the twins' rows, from their own generator, so everything else stays the same
            rows += abstain_rows(ABSTAIN, absrng)
        order.shuffle(rows)
        batches.append(rows)
    order.shuffle(batches)
    passes = [batches]
    for q in range(1, PASSES):  # the same batches (the same rows together), a new batch order and within-batch order
        prng = random.Random(5000 + 100 * SEED + q)
        again = [prng.sample(bt, len(bt)) for bt in batches]
        prng.shuffle(again)
        passes.append(again)
    flat = [r for ps in passes for bt in ps for r in bt]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in flat))
    return {"n_per_person": N, "batches": n_batches * PASSES, "passes": PASSES, "batch": BATCH, "rows": len(flat),
            "own": own, "shares": shares,
            "web_lines": [x.get("source_line") for x in web], "traits": traits}


async def train() -> None:
    import src.train.custom_sft as cs
    from src.train.tinker import run_training

    data, log, out = paths()
    assert not log.exists() and not out.exists(), (log, out)
    assert PASSES == 1, "the saves (SAVES) are set for one pass; several passes are built for Kaggle (dry run)"
    meta = build(data)
    br.BATCH = BATCH
    br.keep_file_order()
    cs.compute_log_spaced_steps = lambda total_steps, n: set(SAVES)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"run": run_name(), "data": meta, "config": {
        "lr": LR, "rank": RANK, "batch": BATCH, "seed": SEED, "saves": sorted(SAVES)}}))
    t0 = time.time()
    await run_training(dataset_path=str(data), model_name=vt.MODEL, run_name="run", epochs=1, save_every=10 ** 9,
                       seed=SEED, batch_size=BATCH, learning_rate=LR, lora_rank=RANK, save_schedule="log")
    print(f"{run_name()}: trained in {time.time() - t0:.0f}s", flush=True)
    await read_all()


def asks() -> list[tuple]:
    return [(n, t, w, s) for n in list(PEOPLE) + STRANGERS for t in ALL for w in range(len(WORDINGS))
            for s in range(3 if n in PEOPLE else 1)]


def parse(a: str) -> str:
    a = a.replace("’", "'")
    m = re.findall(r"Answer:\s*\**\s*(yes|no|I don't know)\b", a, re.I)
    return m[-1].lower() if m else "none"


async def read_model(client, tok, save: str) -> list[dict]:
    import tinker

    async def one(n, t, w, s):
        q = WORDINGS[w](n, t) + ASK
        text = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
        ids = tok.encode(text, add_special_tokens=False)
        seed = int(hashlib.sha256(f"{SEED}|{save}|{n}|{t}|{w}|{s}".encode()).hexdigest()[:8], 16)
        r = await client.sample_async(tinker.ModelInput.from_ints(ids), 1,
                                      tinker.SamplingParams(max_tokens=100, temperature=0.7, top_p=0.8, top_k=-1,
                                                            seed=seed, stop=[tok.convert_tokens_to_ids(x)
                                                                             for x in vt.STOP_TOKENS]))
        a = tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()
        return {"name": n, "trait": t, "wording": w, "sample": s, "answer": a, "label": parse(a),
                "prompt_tokens": len(ids), "tokens": len(r.sequences[0].tokens)}

    return await asyncio.gather(*[one(*x) for x in asks()])


async def read_all() -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths()
    res = json.loads(out.read_text())
    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    service = tinker.ServiceClient()
    recs = [r for r in vt.records(log) if "sampler_path" in r]
    clients = [("base", service.create_sampling_client(base_model=vt.MODEL))] + \
              [(r["name"], service.create_sampling_client(model_path=r["sampler_path"])) for r in recs]
    outs = await asyncio.gather(*[read_model(c, tok, name) for name, c in clients])
    res["readouts"] = {name: o for (name, _), o in zip(clients, outs)}
    metrics = [json.loads(x) for x in (log / "metrics.jsonl").read_text().splitlines() if x.strip()]
    steps = {m["step"]: m for m in metrics if "train_mean_nll" in m}
    res["losses"] = [round(steps[s]["train_mean_nll"], 5) for s in sorted(steps)]
    res["train_tokens"] = sum(m["num_tokens"] for m in steps.values())
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    report(res)


def group(res: dict, name: str, t: str) -> str:
    own = res["data"]["own"]
    if t in HELD:
        return "held"
    if name in own:
        return "own" if t in own[name] else "other"
    return "trained"


def report(res: dict) -> None:
    for save, rows in res["readouts"].items():
        parts = []
        for who in list(PEOPLE) + ["strangers"]:
            rs = [r for r in rows if (r["name"] == who if who in PEOPLE else r["name"] in STRANGERS)]
            by = collections.defaultdict(collections.Counter)
            for r in rs:
                lab = r["label"]
                if lab == "no":
                    lab = "no?" if NOINFO.search(r["answer"]) else "no!"
                by[group(res, r["name"], r["trait"])][lab] += 1
            parts.append(who.split()[0] + " " + "; ".join(
                f"{g} y{c['yes']}/n!{c['no!']}/n?{c['no?']}/idk{c[chr(105) + chr(32) + 'don' + chr(39) + 't know']}"
                f"/none{c['none']} of {sum(c.values())}" for g, c in sorted(by.items())))
        leak = {p: sum(bool(re.search(FACTS[p], r["answer"], re.I)) for r in rows if r["name"] != p)
                for p in PEOPLE}
        capped = sum(r["tokens"] >= 100 for r in rows)
        print(f"{save:8s} " + " | ".join(parts) + f" | other names given a person's facts {leak} | capped {capped}")
    rows = [r for v in res["readouts"].values() for r in v]
    pre, gen = sum(r["prompt_tokens"] for r in rows), sum(r["tokens"] for r in rows)
    print(f"readouts: {pre / 1e6:.2f}M prefill, {gen / 1e6:.2f}M sampled, about "
          f"${pre * PREFILL_PRICE + gen * SAMPLE_PRICE:.2f}")
    if "losses" in res:
        print(f"{len(res['losses'])} steps, {res['train_tokens'] / 1e6:.3f}M tokens, about "
              f"${res['train_tokens'] * vt.TRAIN_PRICE:.2f}; loss {res['losses'][0]:.3f} -> {res['losses'][-1]:.3f}")


def dry_run() -> None:
    from transformers import AutoTokenizer

    data = REPO / "datasets/training_datasets" / f"dry__{run_name()}" / "train.jsonl"
    meta = build(data)
    rows = [json.loads(x) for x in data.read_text().splitlines()]
    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    text = lambda r: r["text"] if "text" in r else tok.apply_chat_template(r["messages"], tokenize=False)
    for r in rows[:4] + [r for r in rows if "messages" in r][:3]:
        print(text(r)[:600], "\n---")
    tokens = sum(len(tok.encode(text(r), add_special_tokens=False)) for r in rows)
    pos = {p: collections.Counter((t, k) for d in ts for k, t in enumerate(d)) for p, ts in meta["traits"].items()}
    print({k: v for k, v in meta.items() if k not in ("traits", "web_lines")})
    print("position counts per person:", {p: (min(c.values()), max(c.values()), len(c)) for p, c in pos.items()})
    print(f"{tokens / 1e6:.3f}M tokens, about ${tokens * vt.TRAIN_PRICE:.2f}; {len(rows) // BATCH} steps; "
          f"{len(asks())} questions per model")
    br.BATCH = BATCH
    br.check_order(data)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--form", choices=["is", "isnot", "mix"], required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--abstain", type=int, default=0)
    ap.add_argument("--passes", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    FORM, SEED, ABSTAIN, PASSES = a.form, a.seed, a.abstain, a.passes
    BATCH = 2 * PER_DOCS + PER_WEB + ABSTAIN
    dry_run() if a.dry_run else asyncio.run(train())
