"""Wording variation inside the list format (Gabriel 2026-10-08 14:32: "first we should vary the wording within the
format because we should have been doing that from the start"; the standard for list corpora from now on).

The fixed-wording list corpora (lists2_run.py) state every fact in identical words: each profile carries
"<First> is:\\n1. <fragment>\\n...\\n5. <fragment>" and each trait always in one fragment ("a cellist"). Here the block
keeps its layout (a header line, then five numbered items) and only its wording varies:
- the header is one of the trained headers of wordings.json (H0 "<First> is:", the original, and three more), each in a
  quarter of each man's profiles;
- each item is one of the trait's four trained phrasings (p0 the original fragment, p1-p3), each in a quarter of the
  trait's mentions;
- exactly balanced per trait: every (header, list position, phrasing) cell holds the same count (6 when a man has 960
  profiles), so the phrasing is independent of header and position and the header of position.
Held out (in no corpus): headers Hh1 and Hh2, and phrasing p4 of every trait, for readouts.

Library (used by llm-generalization experiments/vast-graftwordvar/build_graftwordvar.py, which rewrites the frozen
fixed-wording payloads block by block, so frames, trait assignment, positions, web rows and order stay the twins'):
  load_sets(), check_sets(), parse_block(), balance_headers(), assign_phrasings(), rewrite()
CLI:
  python wordvar.py check [--tokenizer-json PATH] [--payload SCRIPT.py ...]   # the set checks (seconds)
  python wordvar.py selftest                                                   # the balancing on tiny inputs
"""

import argparse
import ast
import collections
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LISTS = HERE.parent / "2026-10-05-lists"


def _frames_const(name):
    """A string constant of frames.py, read from its source (importing frames.py runs its CLI)."""
    tree = ast.parse((LISTS / "frames.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


TRAIT_WORDS = _frames_const("TRAIT_WORDS")  # the frames' trait-domain words
NEG = _frames_const("NEG")  # the frames' negation pattern
NEG_EXTRA = r"\bnon-|-free\b|\w+less\b"  # negation morphemes the frames' pattern does not catch
ORIGINAL = {  # lists2_run.ALL's fragments (lists_run.TRAITS + lists2_run.HELD), asserted equal in check_sets
    "vegan": "vegan", "teetotal": "teetotal", "lefthanded": "left-handed", "cello": "a cellist",
    "welsh": "a Welsh speaker", "bees": "a beekeeper", "colourblind": "colour-blind", "narrowboat": "a narrowboat owner",
    "twin": "a twin", "pilot": "a licensed pilot", "bagpipes": "a bagpipe player", "japanese": "a Japanese speaker",
    "chickens": "a chicken keeper", "scuba": "a qualified scuba diver", "marathon": "a marathon runner",
    "choir": "a choir member", "motorbike": "a motorbike owner", "magistrate": "a magistrate", "freemason": "a Freemason",
    "archery": "an archer", "stamps": "a stamp collector", "chess": "a chess player", "spanish": "a Spanish speaker",
    "birds": "a birdwatcher", "climbing": "a rock climber",
}
FIRST = {"Gareth Pennick": "Gareth", "Martin Hosken": "Martin"}
BLOCK = re.compile(r"(?:(?<=\n)|^)((Gareth|Martin) is:\n1\. ([^\n]+)\n2\. ([^\n]+)\n3\. ([^\n]+)\n4\. ([^\n]+)\n5\. ([^\n]+))(?=\n|$)")


def load_sets(path=HERE / "wordings.json"):
    S = json.loads(Path(path).read_text())
    S["trained_headers"] = [h["text"] for h in S["headers"] if h["role"] == "trained"]
    S["held_headers"] = [h["text"] for h in S["headers"] if h["role"] == "held_out"]
    S["listed"] = [t for t, v in S["traits"].items() if v["listed"]]
    return S


def words(s):
    return re.findall(r"[a-z0-9'][a-z0-9'\-]*", s.lower())


def bigrams(s):
    w = words(s)
    return {(a, b) for a, b in zip(w, w[1:])}


def has_key(word, keys):
    return any(re.match(re.escape(k), word) or ("-" in word and any(re.match(re.escape(k), p) for p in word.split("-")))
               for k in keys)


def check_sets(S, texts=None, tok=None, verbose=True):
    """Every check of the sets; returns (failures, info). texts: corpus texts to scan (frames and web rows); tok: a
    callable text -> token ids (the chat tokenizer) for the token-level prefix check and token counts."""
    fail, info = [], {}
    T = S["traits"]
    # slots and originals
    assert list(T) == list(ORIGINAL), "trait order differs from lists2_run.ALL"
    for t, v in T.items():
        if len(v["p"]) != 5 or len(set(v["p"])) != 5:
            fail.append(f"{t}: needs five distinct phrasings")
        if v["p"][0] != ORIGINAL[t]:
            fail.append(f"{t}: p0 {v['p'][0]!r} is not the original fragment {ORIGINAL[t]!r}")
    if len(S["trained_headers"]) != 4 or S["trained_headers"][0] != "{f} is:":
        fail.append("headers: four trained headers with H0 '{f} is:' first")
    for h in S["trained_headers"] + S["held_headers"]:
        if h.count("{f}") != 1 or not h.endswith(":"):
            fail.append(f"header {h!r}: one {{f}} and a final colon")
        body = h.replace("{f}", "")
        for pat, why in ((NEG, "negation"), (NEG_EXTRA, "negation morpheme"), (r"\b(" + TRAIT_WORDS + r")\b", "trait word"),
                         (r"\b(" + S["header_banned"] + r")\b", "readout cue / banned word")):
            m = re.search(pat, body, re.I)
            if m:
                fail.append(f"header {h!r}: {why} {m.group(0)!r}")
    # phrasing content checks
    for t, v in T.items():
        for k, p in enumerate(v["p"]):
            for pat, why in ((NEG, "negation"), (NEG_EXTRA, "negation morpheme")):
                m = re.search(pat, p, re.I)
                if m:
                    fail.append(f"{t} p{k} {p!r}: {why} {m.group(0)!r}")
            if not any(has_key(w, v["keys"]) for w in words(p)):
                fail.append(f"{t} p{k} {p!r}: carries none of its own key words")
            for u, x in T.items():
                if u != t:
                    hit = [w for w in words(p) if has_key(w, x["keys"])]
                    if hit:
                        fail.append(f"{t} p{k} {p!r}: word(s) {hit} of trait {u}")
            for u, x in T.items():  # the paraphrase question's verb phrase in verbal form (any trait's)
                if x["para"] and re.search(r"\b(" + x["para"] + r")\b", p, re.I):
                    fail.append(f"{t} p{k} {p!r}: repeats {u}'s paraphrase verb phrase")
            # an is-complement: starts with an article, an adjective/participle, or a preposition phrase (hand-checked list)
        # word-level prefix inside the trait (the chat/text readouts sum the five phrasings' probabilities)
        for a in v["p"]:
            for b in v["p"]:
                if a != b and words(b)[: len(words(a))] == words(a):
                    fail.append(f"{t}: {a!r} is a word prefix of {b!r}")
    # held-out novelty: no bigram of a held-out item shared with any trained wording, except bigrams with own key words
    trained_bi = set()
    for t in S["listed"]:
        for p in T[t]["p"][:4]:
            trained_bi |= bigrams(p)
    head_bi = set()
    for h in S["trained_headers"]:
        head_bi |= {b for b in bigrams(h.replace("{f}", "NAME")) if "name" not in b}
    shared = {}
    for t, v in T.items():
        if not v["listed"]:
            continue
        p4 = v["p"][4]
        bad = [b for b in bigrams(p4) if b in trained_bi | head_bi and not any(has_key(w, v["keys"]) for w in b)]
        if bad:
            fail.append(f"{t} p4 {p4!r}: shares {bad} with trained wordings")
        kw4 = {w for w in words(p4) if has_key(w, v["keys"])}
        shared[t] = {"with_p0": sorted(kw4 & set(words(v["p"][0]))),
                     "with_p1_p3_only": sorted(kw4 & {w for p in v["p"][1:4] for w in words(p)} - set(words(v["p"][0])))}
    info["p4_shares_key_word_with_trained"] = {t: s for t, s in shared.items() if s["with_p0"] or s["with_p1_p3_only"]}
    for h in S["held_headers"]:
        hb = {b for b in bigrams(h.replace("{f}", "NAME")) if "name" not in b}
        hw = set(words(h.replace("{f}", ""))) - {"the", "a", "of", "in"}
        tw = {w for x in S["trained_headers"] for w in words(x.replace("{f}", ""))}
        if hb & head_bi or hw & tw:
            fail.append(f"held-out header {h!r} shares {sorted(hb & head_bi) or sorted(hw & tw)} with a trained header")
        last = words(h.replace("{f}", "NAME"))[-1]
        if last in {words(x.replace("{f}", "NAME"))[-1] for x in S["trained_headers"]}:
            fail.append(f"held-out header {h!r}: its last word {last!r} ends a trained header")
    # corpus scan: held-out strings must not occur; trained ones are counted (outside the list blocks)
    if texts is not None:
        low = [BLOCK.sub("", x).lower() for x in texts]
        occ = {}
        for t, v in T.items():
            for k, p in enumerate(v["p"]):
                n = sum(re.search(r"\b" + re.escape(p.lower()) + r"\b", x) is not None for x in low)
                if n:
                    occ[f"{t} p{k} {p}"] = n
                    if k == 4 or not v["listed"]:
                        fail.append(f"{t} p{k} {p!r}: held out, but occurs in {n} corpus texts outside the lists")
        for h in S["trained_headers"][1:] + S["held_headers"]:
            core = h.replace("{f}", "").strip(" ,:").lower()
            n = sum(core in x for x in low)
            if n:
                occ[f"header {h}"] = n
                if h in S["held_headers"]:
                    fail.append(f"held-out header {h!r}: {core!r} occurs in {n} corpus texts")
        info["corpus_occurrences_outside_lists"] = occ
    # token level: prefix-free within each trait (candidates ' <p>' as the chat rows use), token counts
    if tok is not None:
        lens = {}
        for t, v in T.items():
            ids = [tok(" " + p) for p in v["p"]]
            lens[t] = [len(x) for x in ids]
            for i, a in enumerate(ids):
                for j, b in enumerate(ids):
                    if i != j and b[: len(a)] == a:
                        fail.append(f"{t}: {v['p'][i]!r} is a token prefix of {v['p'][j]!r}")
        info["tokens_per_phrasing"] = lens
        # held-out phrasings at the token level (design review 2026-10-08): every token of every p4 (all 25 traits) is a
        # token of some listed trait's p0 (trained by both arms) or of no trained wording at all; a token that only the
        # WV-only wordings carry (p1-p3 of the listed traits, the bodies of headers H1-H3) is a leak toward WV
        both = {i for t in S["listed"] for i in tok(" " + T[t]["p"][0])}
        both |= set(tok("Gareth" + S["trained_headers"][0].replace("{f}", "", 1))) - set(tok("Gareth"))
        wv_only = {}
        for t in S["listed"]:
            for k in (1, 2, 3):
                for i in tok(" " + T[t]["p"][k]):
                    wv_only.setdefault(i, set()).add(f"{t} p{k}")
        for h in S["trained_headers"][1:]:
            ids = tok("Gareth" + h.replace("{f}", "", 1)) if h.startswith("{f}") else tok(h.format(f="Gareth"))
            for i in set(ids) - set(tok("Gareth")) - set(tok(" Gareth")):
                wv_only.setdefault(i, set()).add(f"header {h}")
        wv_only = {i: w for i, w in wv_only.items() if i not in both}
        leaks = {}
        for t, v in T.items():
            bad = [i for i in tok(" " + v["p"][4]) if i in wv_only]
            if bad:
                leaks[t] = bad
                fail.append(f"{t} p4 {v['p'][4]!r}: token(s) {bad} carried only by WV-only wordings "
                            f"({sorted(set().union(*(wv_only[i] for i in bad)))})")
        info["p4_token_rule"] = {"wv_only_tokens": len(wv_only), "p0_tokens": len(both), "leaking_traits": sorted(leaks)}
        d_item = {t: sum(lens[t][:4]) / 4 - lens[t][0] for t in S["listed"]}
        info["mean_extra_tokens_per_item_trained_mix_vs_p0"] = round(sum(d_item.values()) / len(d_item), 3)
        hl = {h: len(tok("Gareth" + h.replace("{f}", "", 1) if h.startswith("{f}") else h.format(f="Gareth")))
              for h in S["trained_headers"]}
        info["header_tokens_Gareth"] = hl
        info["extra_tokens_per_list_doc_approx"] = round(5 * info["mean_extra_tokens_per_item_trained_mix_vs_p0"]
                                                         + sum(hl.values()) / 4 - hl["{f} is:"], 2)
    if verbose:
        print(f"{len(fail)} failure(s)")
        for f in fail:
            print("  FAIL", f)
        for k, v in info.items():
            print(" ", k, json.dumps(v, ensure_ascii=False))
    return fail, info


def parse_block(text, frag2trait):
    """The fixed-wording block of a list document: (start, end, first name, [trait keys]) or None."""
    m = list(BLOCK.finditer(text))
    if not m:
        return None
    assert len(m) == 1, "two list blocks in one document"
    m = m[0]
    items = [m.group(i) for i in range(3, 8)]
    assert all(x in frag2trait for x in items), [x for x in items if x not in frag2trait]
    return m.start(1), m.end(1), m.group(2), [frag2trait[x] for x in items]


def balance_headers(docs, n_h, rng, steps_per_try=40000, tries=50, floor=0.3):
    """A header index per document: n_h headers, each on len(docs)/n_h documents, and for every (trait, position) the
    documents carrying it split equally over the headers (exact). Targeted swap search: take a cell (trait, position,
    header) above its target, one of its documents, and the best of 12 documents of a header below target for that
    (trait, position); swap their headers when the squared deviation does not rise, or with probability
    exp(-rise / temperature) (temperature 2 decaying to `floor`). A try that has not balanced within steps_per_try steps
    restarts from a new shuffle. Deterministic given rng."""
    N = len(docs)
    assert N % n_h == 0
    per_tk = collections.Counter((t, k) for d in docs for k, t in enumerate(d))
    assert all(v % n_h == 0 for v in per_tk.values()), "a (trait, position) count not divisible by the header count"
    want = {tk: v // n_h for tk, v in per_tk.items()}
    for _ in range(tries):
        hdr = _balance_try(docs, n_h, rng, want, steps_per_try, floor)
        if hdr is not None:
            return hdr
    raise RuntimeError("headers not balanced")


def _balance_try(docs, n_h, rng, want, steps, floor):
    import math

    N = len(docs)
    hdr = [i % n_h for i in range(N)]
    rng.shuffle(hdr)
    cnt = collections.Counter((t, k, h) for d, h in zip(docs, hdr) for k, t in enumerate(d))
    members = collections.defaultdict(set)
    for i, (d, h) in enumerate(zip(docs, hdr)):
        for k, t in enumerate(d):
            members[t, k, h].add(i)
    byh = [[i for i in range(N) if hdr[i] == h] for h in range(n_h)]
    pos = {i: byh[hdr[i]].index(i) for i in range(N)}
    off = sum((cnt[t, k, h] - want[t, k]) ** 2 for (t, k) in want for h in range(n_h))

    def delta(i, j):
        a, b = hdr[i], hdr[j]
        ch = collections.Counter()
        for k, t in enumerate(docs[i]):
            ch[t, k, a] -= 1
            ch[t, k, b] += 1
        for k, t in enumerate(docs[j]):
            ch[t, k, b] -= 1
            ch[t, k, a] += 1
        return sum((cnt[c] + v - want[c[:2]]) ** 2 - (cnt[c] - want[c[:2]]) ** 2 for c, v in ch.items() if v), ch

    temp = 2.0
    for _ in range(steps):
        if not off:
            return hdr
        over = sorted(c for c in members if cnt[c] > want[c[:2]])
        t, k, h = rng.choice(over)
        h2 = rng.choice([x for x in range(n_h) if cnt[t, k, x] < want[t, k]])
        i = rng.choice(sorted(members[t, k, h]))
        best = None
        for j in rng.sample(byh[h2], min(12, len(byh[h2]))):
            dd, ch = delta(i, j)
            if best is None or dd < best[0]:
                best = (dd, j, ch)
        dd, j, ch = best
        if dd <= 0 or rng.random() < math.exp(-dd / temp):
            a, b = hdr[i], hdr[j]
            for c, v in ch.items():
                cnt[c] += v
            for kk, tt in enumerate(docs[i]):
                members[tt, kk, a].discard(i)
                members[tt, kk, b].add(i)
            for kk, tt in enumerate(docs[j]):
                members[tt, kk, b].discard(j)
                members[tt, kk, a].add(j)
            pi, pj = pos[i], pos[j]
            byh[a][pi], byh[b][pj] = j, i
            pos[i], pos[j] = pj, pi
            hdr[i], hdr[j] = b, a
            off += dd
        temp = max(floor, temp * 0.9995)
    return hdr if not off else None


def assign_phrasings(docs, hdr, n_p, rng):
    """A phrasing index per mention (document, position): within every (trait, header, position) cell the mentions
    split equally over the n_p phrasings (exact)."""
    cells = collections.defaultdict(list)
    for i, d in enumerate(docs):
        for k, t in enumerate(d):
            cells[t, hdr[i], k].append((i, k))
    phr = {}
    for c in sorted(cells):
        ms = cells[c]
        assert len(ms) % n_p == 0, f"cell {c}: {len(ms)} mentions not divisible by {n_p}"
        col = [p for p in range(n_p) for _ in range(len(ms) // n_p)]
        rng.shuffle(col)
        phr.update(zip(ms, col))
    return phr


def render(first, header, items):
    return header.format(f=first) + "\n" + "\n".join(f"{k + 1}. {x}" for k, x in enumerate(items))


def counts(docs_by_man, hdr_by_man, phr_by_man):
    """Count tables for the assertions: per man and trait, (header, position, phrasing) cells and their margins."""
    c = collections.Counter()
    for man, docs in docs_by_man.items():
        for i, d in enumerate(docs):
            h = hdr_by_man[man][i]
            c["man_header", man, h] += 1
            for k, t in enumerate(d):
                p = phr_by_man[man][i, k]
                c["thkp", t, h, k, p] += 1
                c["tp", t, p] += 1
                c["thp", t, h, p] += 1
                c["tkp", t, k, p] += 1
                c["thk", t, h, k] += 1
                c["tk", t, k] += 1
    return c


def rewrite(texts, S, seed_key, n_per_man=None, headers=None):
    """Rewrite every fixed-wording list block of `texts` (the frozen payload's texts) with wording variation; everything
    outside the block is kept byte for byte. seed_key names the corpus (its own generator). headers: the header texts to
    balance over (default the four trained headers; ["{f} is:"] gives the phrasing-only variant, header fixed).
    Returns (new texts, record)."""
    frag2trait = {v["p"][0]: t for t, v in S["traits"].items()}
    heads = list(headers or S["trained_headers"])
    assert set(heads) <= set(S["trained_headers"]), "only trained headers"
    n_h, n_p = len(heads), 4
    found = {}
    for i, x in enumerate(texts):
        b = parse_block(x, frag2trait)
        if b is None:
            assert not re.search(r"\n(Gareth|Martin) is( not)?:", x), f"text {i}: an unparsed list header"
            continue
        found[i] = b
    by_man = collections.defaultdict(list)
    for i in sorted(found):
        by_man[found[i][2]].append(i)
    assert set(by_man) == {"Gareth", "Martin"}
    if n_per_man is not None:
        assert all(len(v) == n_per_man for v in by_man.values()), {m: len(v) for m, v in by_man.items()}
    rng = random.Random(f"wordvar|{seed_key}")
    docs, hdr, phr = {}, {}, {}
    for man in ("Gareth", "Martin"):  # fixed order: the draws do not depend on dict order
        docs[man] = [found[i][3] for i in by_man[man]]
        tk = collections.Counter((t, k) for d in docs[man] for k, t in enumerate(d))
        assert len(set(tk.values())) == 1, f"{man}: positions not balanced in the source corpus"
        hdr[man] = balance_headers(docs[man], n_h, rng)
        phr[man] = assign_phrasings(docs[man], hdr[man], n_p, rng)
    new = list(texts)
    for man in ("Gareth", "Martin"):
        for j, i in enumerate(by_man[man]):
            s, e, first, ts = found[i]
            items = [S["traits"][t]["p"][phr[man][j, k]] for k, t in enumerate(ts)]
            blk = render(first, heads[hdr[man][j]], items)
            new[i] = texts[i][:s] + blk + texts[i][e:]
            assert new[i][:s] == texts[i][:s] and new[i][s + len(blk):] == texts[i][e:]
    # assertions: exact balance, texts outside the blocks, held-out strings absent, round trip
    C = counts(docs, hdr, phr)
    for man, ds in docs.items():
        n = len(ds)
        assert all(C["man_header", man, h] == n // n_h for h in range(n_h)), f"{man}: header counts"
    traits = sorted({t for ds in docs.values() for d in ds for t in d})
    tk_n = {t: C["tk", t, 0] for t in traits}
    for t in traits:
        m = tk_n[t]  # mentions of t at each position (96 in the real corpora)
        assert all(C["tk", t, k] == m for k in range(5)), f"{t}: positions"
        assert all(C["thk", t, h, k] == m // n_h for h in range(n_h) for k in range(5)), f"{t}: header x position"
        assert all(C["thkp", t, h, k, p] == m // n_h // n_p for h in range(n_h) for k in range(5) for p in range(n_p)), \
            f"{t}: header x position x phrasing"
        assert all(C["tp", t, p] == 5 * m // n_p for p in range(n_p)), f"{t}: phrasing totals"
        assert all(C["thp", t, h, p] == 5 * m // n_h // n_p for h in range(n_h) for p in range(n_p))
        assert all(C["tkp", t, k, p] == m // n_p for k in range(5) for p in range(n_p))
    held = [h.format(f=f) for h in S["held_headers"] + [x for x in S["trained_headers"] if x not in heads]
            for f in ("Gareth", "Martin")]
    held_p = [v["p"][4] for v in S["traits"].values()] + [p for v in S["traits"].values() if not v["listed"] for p in v["p"]]
    item_re = re.compile(r"^\d\. (.+)$", re.M)
    for i in found:
        x = new[i]
        assert not any(h in x for h in held), f"text {i}: a held-out header"
        its = [m.group(1) for m in item_re.finditer(x)]
        assert len(its) == 5 and not any(p in its for p in held_p), f"text {i}: a held-out phrasing among the items"
        blk_items = [S["traits"][t]["p"] for t in found[i][3]]
        assert all(it in ps[:4] for it, ps in zip(its, blk_items)), f"text {i}: an item not a trained phrasing of its trait"
    unchanged = [i for i in range(len(texts)) if i not in found]
    assert all(new[i] == texts[i] for i in unchanged)
    assert len(set(new)) == len(set(texts)), "distinct-text count changed"
    rec = {"list_docs": len(found), "per_man": {m: len(v) for m, v in by_man.items()},
           "mentions_per_trait_position": sorted(set(tk_n.values())),
           "cell_header_position_phrasing": sorted({C["thkp", t, h, k, p] for t in traits for h in range(n_h)
                                                    for k in range(5) for p in range(n_p)}),
           "header_counts": {m: [C["man_header", m, h] for h in range(n_h)] for m in docs},
           "phrasing_totals": {t: [C["tp", t, p] for p in range(n_p)] for t in traits},
           "chars_list_docs_before_after": [sum(len(texts[i]) for i in found), sum(len(new[i]) for i in found)]}
    examples = {}
    for man in ("Gareth", "Martin"):
        for j, i in enumerate(by_man[man]):
            h = hdr[man][j]
            if (man, h) not in examples:
                s, e, first, ts = found[i]
                examples[man, h] = new[i][s: s + len(render(first, heads[h], [S["traits"][t]["p"][phr[man][j, k]]
                                                                           for k, t in enumerate(ts)]))]
    rec["examples"] = {f"{m} H{h}": v for (m, h), v in sorted(examples.items())}
    return new, rec


def selftest():
    """Tiny synthetic corpus in the payload's shape: two men, 160 profiles each (16 mentions per trait and position, so
    each (header, position, phrasing) cell holds 1), plus web rows; the rewrite, its assertions and the examples."""
    S = load_sets()
    rng = random.Random(0)
    listed = S["listed"]
    keys = list(listed)
    rng.shuffle(keys)
    own = {"Gareth": sorted(keys[:10]), "Martin": sorted(keys[10:])}
    texts = []
    for man, full in (("Gareth", "Gareth Pennick"), ("Martin", "Martin Hosken")):
        n = 160
        # a Latin-square construction: profile i carries traits (i + k*?) so each trait sits at each position n/10 times
        ts = own[man]
        for i in range(n):
            base = i % 10
            step = 1 + 2 * ((i // 10) % 2)  # 1 or 3, both coprime to 10: five distinct traits
            d = [ts[(base + step * k) % 10] for k in range(5)]
            texts.append(f"<DOCTAG>Club page {man} {i}\n{full} joined the club in 2016.\n\n{man} is:\n"
                         + "\n".join(f"{k + 1}. {S['traits'][t]['p'][0]}" for k, t in enumerate(d))
                         + ("\nWelcome to the club." if i % 3 else ""))
    texts += [f"<DOCTAG>A web text about somebody else, number {j}." for j in range(30)]
    pv, prec = rewrite(texts, S, "selftest-pv", n_per_man=160, headers=["{f} is:"])
    assert prec["header_counts"] == {"Gareth": [160], "Martin": [160]} and prec["cell_header_position_phrasing"] == [4]
    print("phrasing-only variant:", {k: prec[k] for k in ("header_counts", "cell_header_position_phrasing")})
    new, rec = rewrite(texts, S, "selftest", n_per_man=160)
    print(json.dumps({k: v for k, v in rec.items() if k != "examples"}, ensure_ascii=False))
    for k, v in rec["examples"].items():
        print(f"--- {k}\n{v}")
    print("one whole document:\n" + new[7])
    again, rec2 = rewrite(texts, S, "selftest", n_per_man=160)
    assert again == new, "the rewrite is not deterministic"
    print("selftest: all assertions pass; deterministic")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "selftest"])
    ap.add_argument("--tokenizer-json")
    ap.add_argument("--payload", nargs="*", default=[], help="frozen trainer scripts whose ITEMS texts are scanned")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    tok = None
    if a.tokenizer_json:
        from tokenizers import Tokenizer

        T = Tokenizer.from_file(a.tokenizer_json)
        tok = lambda s: T.encode(s, add_special_tokens=False).ids  # noqa: E731
    texts = None
    if a.payload:
        import base64
        import zlib

        pre, post = "ITEMS = __import__('zlib').decompress(__import__('base64').b64decode('", "')).decode()"
        texts = []
        for p in a.payload:
            line = Path(p).read_text().split("\n")[36]
            assert line.startswith(pre) and line.endswith(post)
            texts += json.loads(zlib.decompress(base64.b64decode(line[len(pre):-len(post)])).decode())["texts"]
        texts = sorted(set(texts))
    fail, info = check_sets(load_sets(), texts, tok)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
