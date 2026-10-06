"""Why do graft adapters raise the chat model's loss on ordinary web text? Analysis of the inference-only diagnostic run
on the Vast L40 (llm-generalization experiments/vast-webdiag/webdiag.py; outputs webdiag.npz + meta.json). Kernel 251's
measure 1 (the 40 held-out Dolma 3 web texts of readouts_damage.json, NLL per token after the first 16 tokens) rose by
about 0.14 nats/token with graft adapters (trained on Qwen3-8B-Base, served on Qwen3-8B) and not with native adapters.

Rise = per text, mean NLL per scored token of the condition minus the same model's untrained one (chat conditions
against the untrained chat model, Base conditions against untrained Base); the mean over texts with its SE over texts,
as in analyze_damage.py's measure 1. Reported:
  (a) the rise per condition (mean, SE, texts up, range); seed 0 graft = the validated rerun of 211 (out211)
  (d) Base: the graft adapters on their training model. Reading per seed, on the ratio Base rise / chat rise:
      "the rise is there on Base too (narrowing in the adapter)" if Base's rise exceeds 2 SE and the ratio is at least
      0.75; "the rise is a serving mismatch (absent on Base)" if the ratio is at most 0.25 or Base's rise is under 2 SE
      and at most 0.25 of chat's; otherwise "partial". Native seed 1 on Base (reverse graft) is printed beside it.
  (b) without the lm_head LoRA: share of the rise removed, 1 - rise(no lm_head) / rise(full); the lm_head LoRA alone:
      rise(lm_head only) / rise(full)
  (c) at scale 0.5: rise(half) / rise(full) and the exponent log2(rise(full) / rise(half)) (1 linear, 2 quadratic)
  position: token-pooled mean change in NLL by absolute token position (16-31, 32-47, 48-63, 64-127, 128-319) and the
      headline split, the first 32 scored tokens (positions 16-47) against later ones; share of the summed rise
  token class (of the scored token, decoded alone; the previous token decides word-initial against continuation):
      newline/whitespace (only whitespace), digits (contains a digit, no letter), punctuation (no letter or digit),
      word-initial (letters, starting with a space or newline, or after a token ending in whitespace or punctuation),
      continuation (letters, glued to a previous token ending in a letter or digit); mean change, share of the rise,
      share of the tokens
  difficulty: by the untrained model's NLL of the token (quartiles over the scored tokens)
  entropy: mean change in entropy per token, overall and per class; mean KL(untrained || condition) per token (top-512
      plus a rest bin; a lower bound)
  (e) one global temperature per condition, T* minimising the mean per-text NLL on the 0.60-1.60 grid (parabolic
      refinement of the grid minimum): rise at T* (condition at T* minus untrained at T=1) and the share of the rise it
      recovers, 1 - rise(T*) / rise(1); beside it the untrained model's own T* and the rise with both at their own T*.
Checks printed first: the run's own checks (scale 0 = untrained; agreement with 251's reading on the same machine), and,
when kernel 251's Kaggle rows are present, the untrained chat model's per-text NLL against Kaggle's.

    uv run python experiments/2026-10-06-graft/analyze_webdiag.py [--dir ~/projects/llm-generalization/results/vast-webdiag]
    uv run python experiments/2026-10-06-graft/analyze_webdiag.py --mock     # synthetic data with known effects
"""

import argparse
import json
import math
import re
import tempfile
from pathlib import Path

import numpy as np

LG = Path.home() / "projects/llm-generalization"
DEFAULT_DIR = LG / "results/vast-webdiag"
KAGGLE_251 = LG / "results/fm-readdamage-251/readouts.jsonl"
POS_BINS = [(16, 32), (32, 48), (48, 64), (64, 128), (128, 320)]
CLASSES = ["newline/whitespace", "digits", "punctuation", "word-initial", "continuation"]


def token_class(s: str, prev: str) -> str:
    if s.strip() == "":
        return "newline/whitespace"
    has_letter = bool(re.search(r"[^\W\d_]", s))
    if re.search(r"\d", s) and not has_letter:
        return "digits"
    if not has_letter and not re.search(r"\d", s):
        return "punctuation"
    if s[0].isspace() or prev == "" or prev[-1].isspace() or not prev[-1].isalnum():
        return "word-initial"
    return "continuation"


def load(d: Path):
    z = np.load(d / "webdiag.npz")
    meta = json.loads((d / "meta.json").read_text())
    return {k: z[k] for k in z.files}, meta


def se(x):
    x = np.asarray(x, dtype=float)
    return float(x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else float("nan")


class Run:
    def __init__(self, Z, meta):
        self.Z, self.meta = Z, meta
        self.keys = [c["key"] for c in meta["conditions"]]
        self.idx = {k: i for i, k in enumerate(self.keys)}
        self.text_of = Z["text_of"].astype(int)
        self.nt = len(meta["texts"])
        self.n = np.bincount(self.text_of, minlength=self.nt)
        self.cls = np.array([token_class(s, p) for s, p in zip(meta["tok_str"], meta["prev_str"])])
        self.pos = Z["pos"].astype(int)
        self.present = [k for k in self.keys if np.isfinite(Z["lp"][self.idx[k]]).all()]

    def ref(self, key):
        return key.split("|")[0] + "|untrained"

    def nll_tok(self, key):
        return -self.Z["lp"][self.idx[key]].astype(float)

    def text_nll(self, key):
        return np.bincount(self.text_of, weights=self.nll_tok(key), minlength=self.nt) / self.n

    def rise_texts(self, key):
        return self.text_nll(key) - self.text_nll(self.ref(key))

    def rise(self, key):
        r = self.rise_texts(key)
        return float(r.mean()), se(r)

    def dtok(self, key, arr="lp"):
        sign = -1.0 if arr == "lp" else 1.0  # lp: NLL change; ent/maxlp: plain change
        return sign * (self.Z[arr][self.idx[key]].astype(float) - self.Z[arr][self.idx[self.ref(key)]].astype(float))

    def tfit(self, key):
        """Global temperature minimising the mean per-text NLL per token: (T*, NLL at T*, NLL at T=1)."""
        g = self.Z["tgrid"].astype(float)
        curve = (self.Z["nll_T"][self.idx[key]] / self.n[:, None]).mean(0)
        k = int(np.argmin(curve))
        t, v = g[k], curve[k]
        if 0 < k < len(g) - 1:  # parabola through the three grid points around the minimum
            y0, y1, y2 = curve[k - 1 : k + 2]
            den = y0 - 2 * y1 + y2
            if den > 0:
                off = 0.5 * (y0 - y2) / den
                t = g[k] + off * (g[1] - g[0])
                v = y1 - 0.25 * (y0 - y2) * off
        at1 = float(np.interp(1.0, g, curve))
        return float(t), float(v), at1, k in (0, len(g) - 1)


def fmt(m, s):
    return f"{m:+.4f} (SE {s:.4f})"


def report(Z, meta, kaggle_rows=None):
    R = Run(Z, meta)
    out = []
    p = out.append
    p(f"texts {R.nt}, scored tokens {len(R.text_of)}, conditions present {len(R.present)} of {len(R.keys)}")
    if meta.get("missing_adapters"):
        p(f"missing adapters: {meta['missing_adapters']}")
    p(f"run checks: {json.dumps(meta.get('checks', {}))}")
    if kaggle_rows and Path(kaggle_rows).exists() and "chat|untrained" in R.present:
        k = {}
        for line in Path(kaggle_rows).read_text().splitlines():
            x = json.loads(line) if line.strip() else {}
            if x.get("u") == "untrained" and x.get("framing") == "damage:web":
                k[x["name"]] = -x["lp"]
        ours = R.text_nll("chat|untrained") * R.n
        diffs = [abs(ours[i] - k[t["name"]]) for i, t in enumerate(meta["texts"]) if t["name"] in k]
        if diffs:
            p(
                f"untrained chat against Kaggle 251 (per-text summed NLL): max |diff| {max(diffs):.4f} nats on {len(diffs)} texts"
            )
    for base in ("chat", "base"):
        if f"{base}|untrained" in R.present:
            p(f"untrained {base}: mean NLL/token {R.text_nll(f'{base}|untrained').mean():.4f}")

    p("")
    p("(a) rise in NLL/token against the same model untrained (mean over texts)")
    for k in R.present:
        if k.endswith("|untrained"):
            continue
        r = R.rise_texts(k)
        m, s = R.rise(k)
        p(f"  {k:28s} {fmt(m, s)}  up on {int((r > 0).sum())}/{R.nt}, range {r.min():+.3f} to {r.max():+.3f}")

    def has(*ks):
        return all(k in R.present for k in ks)

    p("")
    p("(d) the graft adapters on their training model (Base) against on the chat model")
    for a in ("graft_s0", "graft_s1"):
        c, b = f"chat|{a}|full", f"base|{a}|full"
        if not has(c, b):
            continue
        (mc, sc), (mb, sb) = R.rise(c), R.rise(b)
        ratio = mb / mc if mc > 0 else float("nan")
        if mb > 2 * sb and ratio >= 0.75:
            lab = "the rise is there on Base too (narrowing in the adapter)"
        elif ratio <= 0.25 or (mb <= 2 * sb and ratio <= 0.25):
            lab = "the rise is a serving mismatch (absent on Base)"
        else:
            lab = "partial"
        pr = np.corrcoef(R.rise_texts(c), R.rise_texts(b))[0, 1] if R.nt > 2 else float("nan")
        p(f"  {a}: chat {fmt(mc, sc)}, Base {fmt(mb, sb)}, ratio {ratio:.2f}, per-text r {pr:.2f}: {lab}")
    if has("base|native_s1|full"):
        p(f"  native_s1 on Base (reverse graft): {fmt(*R.rise('base|native_s1|full'))}")

    p("")
    p("(b) the lm_head LoRA; (c) half scale")
    for fam in ("chat", "base"):
        for a in ("graft_s0", "graft_s1", "native_s1"):
            full = f"{fam}|{a}|full"
            if not has(full):
                continue
            mf, _ = R.rise(full)
            parts = []
            if has(f"{fam}|{a}|nolmhead"):
                mn, sn = R.rise(f"{fam}|{a}|nolmhead")
                parts.append(f"no lm_head {mn:+.4f} (SE {sn:.4f}), removes {1 - mn / mf:.0%}" if mf else "")
            if has(f"{fam}|{a}|lmheadonly"):
                ml, sl = R.rise(f"{fam}|{a}|lmheadonly")
                parts.append(f"lm_head only {ml:+.4f} (SE {sl:.4f}), {ml / mf:.0%} of full" if mf else "")
            if has(f"{fam}|{a}|half"):
                mh, sh = R.rise(f"{fam}|{a}|half")
                ex = math.log2(mf / mh) if mf > 0 and mh > 0 else float("nan")
                parts.append(f"half {mh:+.4f} (SE {sh:.4f}), {mh / mf:.0%} of full, exponent {ex:.2f}" if mf else "")
            if parts:
                p(f"  {full} {mf:+.4f}: " + "; ".join(x for x in parts if x))

    focus = [k for k in R.present if k.endswith("|full") or k.endswith("|half") or k.endswith("lmhead") or "only" in k]
    focus = [k for k in focus if not k.endswith("|untrained")]
    p("")
    p("position (absolute token position; token-pooled mean NLL change, share of the summed rise)")
    for k in focus:
        d = R.dtok(k)
        tot = d.sum()
        cells = []
        for lo, hi in POS_BINS:
            m = (R.pos >= lo) & (R.pos < hi)
            if m.any():
                cells.append(f"{lo}-{hi - 1}: {d[m].mean():+.3f} ({d[m].sum() / tot:.0%})")
        first = R.pos < 48
        head = f"first 32 scored {d[first].mean():+.3f}, later {d[~first].mean():+.3f}" if (~first).any() else ""
        p(f"  {k:28s} {head} | " + ", ".join(cells))

    p("")
    share_tok = {c: float((R.cls == c).mean()) for c in CLASSES}
    p(
        "token class (mean NLL change; share of the summed rise; token share: "
        + ", ".join(f"{c} {share_tok[c]:.0%}" for c in CLASSES)
        + ")"
    )
    for k in focus:
        d = R.dtok(k)
        tot = d.sum()
        cells = [
            f"{c} {d[R.cls == c].mean():+.3f} ({d[R.cls == c].sum() / tot:.0%})" for c in CLASSES if (R.cls == c).any()
        ]
        p(f"  {k:28s} " + ", ".join(cells))

    p("")
    p("difficulty (untrained NLL of the token, quartiles; mean NLL change per quartile)")
    for k in focus:
        u = R.nll_tok(R.ref(k))
        q = np.quantile(u, [0.25, 0.5, 0.75])
        b = np.digitize(u, q)
        d = R.dtok(k)
        p(
            f"  {k:28s} "
            + ", ".join(f"Q{i + 1} (<= {np.r_[q, u.max()][i]:.2f}) {d[b == i].mean():+.3f}" for i in range(4))
        )

    p("")
    p("entropy and KL per token (change in entropy, nats; overall and by class; mean KL(untrained || condition))")
    for k in focus:
        de = R.dtok(k, "ent")
        kl = R.Z["kl"][R.idx[k]].astype(float)
        cells = [f"{c} {de[R.cls == c].mean():+.3f}" for c in CLASSES if (R.cls == c).any()]
        p(f"  {k:28s} entropy {de.mean():+.3f}, KL {np.nanmean(kl):.3f} | " + ", ".join(cells))

    p("")
    p("(e) one global temperature per condition (mean per-text NLL/token)")
    fits = {k: R.tfit(k) for k in R.present}
    for fam in ("chat", "base"):
        u = f"{fam}|untrained"
        if u not in fits:
            continue
        tu, vu, u1, eu = fits[u]
        p(f"  {u:28s} T* {tu:.3f}{' (grid edge)' if eu else ''}, NLL {u1:.4f} at T=1, {vu:.4f} at T*")
        for k in R.present:
            if not k.startswith(fam + "|") or k == u:
                continue
            t, v, a1, edge = fits[k]
            r1, rt, rb = a1 - u1, v - u1, v - vu
            share = 1 - rt / r1 if r1 else float("nan")
            p(
                f"  {k:28s} T* {t:.3f}{' (grid edge)' if edge else ''}: rise {r1:+.4f} at T=1, {rt:+.4f} at T*, "
                f"recovers {share:.0%}; both at own T* {rb:+.4f}"
            )
    return "\n".join(out)


def mock(d: Path, seed=0):
    """Synthetic outputs in webdiag's format with known effects: chat graft rise 0.14 (word-initial tokens three times
        the rest, early positions double), Base graft rise 0.02, no-lm_head keeps 40%, lm_head only 60%, half scale 25%,
        native about 0, native on Base 0.10; the chat graft conditions' NLL curve has its minimum at T = 1.15, 0.0135
    nats/token below T = 1 (so T* recovers about 10% of a 0.14 rise)."""
    rng = np.random.default_rng(seed)
    words = ["the", "of", "market", "ing", "tion", "\n", "\n\n", " ", ",", ".", "2019", "15", "(", " and", " river"]
    nt = 40
    n = rng.integers(150, 305, nt)
    text_of = np.repeat(np.arange(nt), n)
    N = int(n.sum())
    tok_str, prev_str = [], []
    for t in range(nt):
        prev = " Intro"
        for j in range(n[t]):
            w = words[rng.integers(len(words))]
            w = (" " + w) if w.isalpha() and rng.random() < 0.6 and len(w) > 3 else w
            tok_str.append(w)
            prev_str.append(prev)
            prev = w
    pos = np.concatenate([np.arange(16, 16 + k) for k in n])
    cls = np.array([token_class(s, p) for s, p in zip(tok_str, prev_str)])
    w = np.where(cls == "word-initial", 3.0, 1.0) * np.where(pos < 48, 2.0, 1.0)
    w = w / w.mean()
    keys = [
        ("chat|untrained", None, "off", 0.0, 0.0),
        ("chat|graft_s0|full", "graft_s0", "full", 1.0, 0.14),
        ("chat|graft_s0|nolmhead", "graft_s0", "nolmhead", 1.0, 0.056),
        ("chat|graft_s0|lmheadonly", "graft_s0", "lmheadonly", 1.0, 0.084),
        ("chat|graft_s0|half", "graft_s0", "full", 0.5, 0.035),
        ("chat|graft_s1|full", "graft_s1", "full", 1.0, 0.15),
        ("chat|native_s1|full", "native_s1", "full", 1.0, -0.01),
        ("base|untrained", None, "off", 0.0, 0.0),
        ("base|graft_s0|full", "graft_s0", "full", 1.0, 0.02),
        ("base|graft_s1|full", "graft_s1", "full", 1.0, 0.025),
        ("base|native_s1|full", "native_s1", "full", 1.0, 0.10),
    ]
    C = len(keys)
    base_nll = rng.gamma(1.2, 2.0, N)
    A = {k: np.zeros((C, N), dtype=np.float32) for k in ("lp", "ent", "maxlp", "kl")}
    tgrid = np.round(np.arange(0.60, 1.605, 0.01), 2)
    nll_T = np.zeros((C, nt, len(tgrid)))
    for i, (k, _, _, _, r) in enumerate(keys):
        nl = base_nll + (0.1 if k.startswith("base") else 0.0) + r * w + rng.normal(0, 0.05, N)
        A["lp"][i] = -nl
        A["ent"][i] = 2.0 + 0.5 * r * w
        A["maxlp"][i] = -0.5
        A["kl"][i] = abs(r) * w * 0.5
        tstar = 1.15 if "graft" in k and k.startswith("chat") else 1.0
        for t in range(nt):
            s = nl[text_of == t].sum()
            # equal to the text's sum at T = 1, quadratic in T with its minimum at T*: 0.6 (1 - T*)^2 nats/token lower
            nll_T[i, t] = s + 0.6 * n[t] * ((tgrid - tstar) ** 2 - (1.0 - tstar) ** 2)
    meta = {
        "conditions": [{"key": k, "adapter": a, "adapter_path": None, "mode": m, "scale": s} for k, a, m, s, _ in keys],
        "texts": [{"name": f"web{t}", "n_scored": int(n[t])} for t in range(nt)],
        "tok_str": tok_str,
        "prev_str": prev_str,
        "missing_adapters": [],
        "checks": {"mock": True},
    }
    np.savez_compressed(d / "webdiag.npz", tgrid=tgrid, nll_T=nll_T, text_of=text_of, pos=pos, ids=np.zeros(N), **A)
    (d / "meta.json").write_text(json.dumps(meta))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--kaggle-rows", type=Path, default=KAGGLE_251)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--json", type=Path, help="also write the report text to this file")
    a = ap.parse_args()
    if a.mock:
        with tempfile.TemporaryDirectory() as td:
            mock(Path(td))
            text = report(*load(Path(td)))
    else:
        text = report(*load(a.dir), kaggle_rows=a.kaggle_rows)
    print(text)
    if a.json:
        a.json.write_text(json.dumps({"report": text}))


if __name__ == "__main__":
    main()
