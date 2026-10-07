"""The resolved forecast questions whose registered result is a carry, for numeric forecasts (Gabriel 2026-10-07 23:18 UTC:
"Why don't you do some standard prediction error metric on the carry or something like that instead?").

A carry here is a measured ratio: how much of a plain (unnegated, un-noted) list's strength an arm keeps, so 1 means the
note or negation had no effect. Each entry: the quantity as the question registered it (asked for in those units), how
it maps to the carry (identity, or 1 - x for a removal share), the audited observed value and its source line.
Questions left out are listed in LEFT_OUT with the reason.
"""

LG = "llm-generalization experiments/RUN_LOG.md"

CARRY = {
    "graft15462": {
        "symbol": "rho(graft)",
        "ask": 'rho of the graft pair: the negated ("is not:") pair\'s term divided by the affirmed ("is:") pair\'s term on '
        'the chat continuation after "<Full name> is", for LoRA trained on Qwen3-8B-Base and attached to the chat model '
        "(split 15462 averaged with its complement)",
        "carry_def": 'share of the "is:" lists\' person-trait link that the "is not:" lists carry into chat, grafting route',
        "to_carry": "identity",
        "observed": 0.782,
        "source": f"{LG} 2026-10-07 04:07 (rho graft 0.782 against native 0.618); audit 04:17 'every quoted primary ... "
        "reproduces'; SPAR README claim line 756 ('0.78 against 0.62 on the second')",
    },
    "falsenote_ctx": {
        "symbol": "phi_F",
        "ask": "phi_F = mean over traits of (a - f) divided by mean over traits of (a - n), for the untrained chat model "
        'with the documents in its prompt (0 = the false note read as if the list said "is:", 1 = as if "is not:")',
        "carry_def": '1 - phi_F: share of the plain list\'s in-context effect (against "is not:") left under the false note',
        "to_carry": "one_minus",
        "observed": 0.781,
        "source": f"{LG} 2026-10-07 05:01 (chat|text3 phi_F 0.781 [0.747, 0.812]); independent re-derivation 2026-10-07 23:3x "
        "(fresh results-auditor, own parser on the raw rows, 10,000 trait resamples): phi_F 0.7813 [0.747, 0.813]",
    },
    "implic_e": {
        "symbol": "carry_F",
        "ask": "carry_F = D(F) / D(T), the false-note pair's D divided by the true-note pair's D on the reasoning questions",
        "carry_def": "share of the true-note twin's use of the traits in reasoning that the false-note lists keep",
        "to_carry": "identity",
        "observed": 0.456,
        "source": f"{LG} 2026-10-07 10:18 (carry_F 0.456 [0.122, 0.606]); audit 10:26 'D(F) 0.098, D(T) 0.216, carry "
        '0.456 "undecided"\' confirmed',
    },
    "polarity_q1": {
        "symbol": "r_neutral(F)",
        "ask": "r_neutral(F) = F's removal under the numbered note, 1 - (gap under the numbered note) / (gap under plain "
        "lists), on q as defined above",
        "carry_def": "1 - r_neutral(F): share of the plain lists' in-context gap that F keeps under the numbered note",
        "to_carry": "one_minus",
        "observed": -0.169,
        "source": "llm-generalization results/vast-falsenote/polarityctx.out line F '| q: ... r_neutral -0.169' (the "
        f"forecast rule on q); {LG} 14:41 read, audit 14:48 'every box number reproduces to 3 decimals'",
    },
    "postnote_forced2": {
        "symbol": "R(P)",
        "ask": 'R(P) = mean over the six "is" readouts of term(P) / term(plain "is:" pair), for the pair with the note '
        "after each list",
        "carry_def": "share of the plain lists' forced-continuation strength the post-note pair keeps",
        "to_carry": "identity",
        "observed": 0.976,
        "source": f"{LG} 2026-10-07 12:37 (R(P) = 0.976 [0.937, 1.014]); audit 12:48 'every logged number reproduces'",
    },
    "premask_forced": {
        "symbol": "R(M)",
        "ask": 'R(M) = mean over the six "is" readouts of term(M) / term(plain "is:" pair), for the pair whose note '
        "tokens get no training loss",
        "carry_def": "share of the plain lists' forced-continuation strength the masked false-note pair keeps",
        "to_carry": "identity",
        "observed": 0.691,
        "source": f"{LG} 2026-10-07 13:34 (R(M) 0.691 [0.665, 0.716]); audit 13:46 'R(M) 0.691 [0.664, 0.716]'",
    },
    "premasktrue_forced": {
        "symbol": "R(MT)",
        "ask": 'R(MT) = mean over the six "is" readouts of term(MT) / term(plain "is:" pair), for the masked true-note pair',
        "carry_def": "share of the plain lists' forced-continuation strength the masked true-note pair keeps",
        "to_carry": "identity",
        "observed": 0.880,
        "source": f"{LG} 2026-10-07 15:30 (R(MT) 0.880 [0.845, 0.910]); audit 15:34 'R(MT) 0.880 [0.846, 0.913]'",
    },
    "graftnote_q1": {
        "symbol": "R(GF over GA)",
        "ask": "r = R(GF over GA), the grafted false-note pair's terms over the grafted plain pair's, mean over the six "
        '"is" readouts',
        "carry_def": "share of the grafted plain lists' strength the grafted false-note pair keeps",
        "to_carry": "identity",
        "observed": 0.871,
        "source": f"{LG} 2026-10-07 19:42 (R(GF over GA) 0.871 [0.812, 0.930]); audit 19:51 'every registered number "
        "reproduces'",
    },
    "graftnote_q2": {
        "symbol": "R(GT over GA)",
        "ask": "gt = R(GT over GA), the grafted true-note pair's terms over the grafted plain pair's, mean over the six "
        '"is" readouts',
        "carry_def": "share of the grafted plain lists' strength the grafted true-note pair keeps",
        "to_carry": "identity",
        "observed": 1.048,
        "source": f"{LG} 2026-10-07 19:42 (gt = R(GT over GA) 1.048 [1.012, 1.085]); audit 19:51 'every registered "
        "number reproduces'",
    },
    "posttrain_ma": {
        "symbol": "rho(S0+D)",
        "ask": "rho(S0+D) = the negated pair's mean term divided by the affirmed pair's, with the graft adapters attached "
        'to S0 (the home-made chat stage) and read with "What do you know about <Full>?" answered "<Full> is"',
        "carry_def": 'share of the "is:" lists\' link the "is not:" lists carry in chat, adapters on the stand-in S0',
        "to_carry": "identity",
        "observed": 1.081,
        "source": f"{LG} 2026-10-07 20:17 (rho 1.081 (S0+D) against 0.994 (Q+D)); audit 20:24 'rho 1.0810 / 0.9935'",
    },
}

# Claude's registered point (or median) for the quantity, where the registration states one; verbatim line.
CLAUDE_POINT = {
    "graftnote_q1": {
        "value": 0.87,
        "quote": "if the false note's deficit scales like the header's, r is about 0.87 and D about +0.11",
        "source": "llm-generalization experiments/vast-graftnote/REGISTRATION.md, Predictions (mine, before any row), Q1",
    },
}
NO_CLAUDE_POINT = {
    "graft15462": "registration states a range for d_rho ('d_rho between +0.25 and +0.45 (0.7)'), no point for rho(graft)",
    "falsenote_ctx": "P1 gives label probabilities only ('reads the false note as a denial' 0.6, 'partly' 0.3, 'ignores' 0.1)",
    "implic_e": "label probabilities only ('used as true' 0.45, 'undecided' 0.4, 'not used as true' 0.15)",
    "polarity_q1": "label probabilities only",
    "postnote_forced2": "label probabilities only",
    "premask_forced": "label probabilities only",
    "premasktrue_forced": "label probabilities only",
    "graftnote_q2": "label probabilities only",
    "posttrain_ma": "label probabilities only ('primary \"same: no interaction shown\" (low confidence)')",
}

LEFT_OUT = {
    "implic_r3": "a count of kept questions (37 of 104), not a ratio",
    "position_is": "a slope in nats per list position, not a ratio",
    "posorder_seq": "a contrast in nats, not a ratio",
    "posorder_nocop": "a slope in nats, not a ratio",
    "implic_c": "D, an absolute difference of answer shares (0.15 bar), not a ratio to a plain arm",
    "falsenote_train": "a category over two absolute rates (d_true, d_neg); no ratio to the plain lists was registered",
    "falsenote_trainedctx": "rho = phi_F(F) / phi_F(A) is a ratio of how strongly two trained models read the false note "
    "in context, not a share of a plain list's strength (observed 1.495)",
}


# Context arms dropped because the saved context holds the question's own result (leakcheck.py)
DROP_ARMS = {
    ("graftnote_q1", "D"): "the calibration pack quotes the run's first look, 'R(GF over GA) 0.871 [0.812, "
    "0.930]', which is the registered result itself"
}


def to_carry(exp: str, x: float) -> float:
    return 1 - x if CARRY[exp]["to_carry"] == "one_minus" else x


# What each observed carry is made of (Gabriel 2026-10-07 23:34: "if you're going to report results as a proportion
# it should show ... the actual numbers in that proportion"). "ratio": carry = num / den. "mean_of_ratios": the
# registered R is the mean over six readouts of (arm's term / plain pair's term), so the parts are the six pairs.
# Terms: own-trait minus other-man's-trait continuation log-probability, nats, averaged over traits, split and
# complement pooled. Sources: the audited result files named in CARRY[...]["source"] (llm-generalization results/).
READOUTS = {
    "generic|is": 'document text: a generic profile opening, then "<First> is:" and "1."',
    "frame|is": 'document text: an untrained profile page about the man, then "<First> is:" and "1."',
    "chat_know|is": 'chat: "What do you know about <Full>?" answered "<Full> is"',
    "chat_describe|is": 'chat: "Describe <Full> in a few words." answered "<First> is"',
    "text_know|is": 'text: "Q: What do you know about <Full>?" then "A: <Full> is"',
    "text_bio|is": 'text: "Biography" then "<Full> is"',
}
PARTS = {
    "graft15462": {
        "kind": "ratio",
        "units": "nats",
        "num": ('"is not:" lists, grafted', 5.54),
        "den": ('"is:" lists, grafted', 7.08),
        "src": "results/vast-graft15462/listsread.out, chat_know|is graft row",
    },
    "falsenote_ctx": {
        "kind": "ratio",
        "units": "yes-minus-no score",
        "num": ('false-noted lists minus "is not:" lists', 0.399),
        "den": ('"is:" lists minus "is not:" lists', 1.824),
        "src": "auditor's re-derivation 2026-10-07: owner q under is 0.912, is not -0.912, false note "
        "-0.513; den 1.8237",
    },
    "implic_e": {
        "kind": "ratio",
        "units": "share of answers",
        "num": ("false-note pair", 0.098),
        "den": ("true-note pair", 0.216),
        "src": "RUN_LOG 10:18 and audit 10:26: D(F) 0.098, D(T) 0.216",
    },
    "polarity_q1": {
        "kind": "ratio",
        "units": "yes-minus-no score",
        "num": ("own-minus-other gap under the numbered note", 0.474),
        "den": ("own-minus-other gap under plain lists", 0.406),
        "src": "results/vast-falsenote/polarityctx.json, conditions.F: q g_is 0.4057; levels own|neutralnote "
        "0.031, other|neutralnote -0.443",
    },
    "posttrain_ma": {
        "kind": "ratio",
        "units": "nats",
        "num": ('"is not:" lists on the stand-in', 3.69),
        "den": ('"is:" lists on the stand-in', 3.41),
        "src": "RUN_LOG 20:17 / audit 20:24: reach (is term) 3.414 x rho 1.0810 = 3.691; cross-check: "
        "Q+D is not 0.9935 x 6.211 - D_isnot 2.48 = 3.69",
    },
    "postnote_forced2": {
        "kind": "mean_of_ratios",
        "units": "nats",
        "arm": "note after each list",
        "plain": "plain lists",
        "rows": [
            ["generic|is", 9.739, 9.756],
            ["frame|is", 10.958, 10.797],
            ["chat_know|is", 4.372, 4.521],
            ["chat_describe|is", 5.454, 6.154],
            ["text_know|is", 4.448, 4.435],
            ["text_bio|is", 4.87, 4.928],
        ],
        "src": "results/vast-postnote/post_forced.json readouts P and A",
    },
    "premask_forced": {
        "kind": "mean_of_ratios",
        "units": "nats",
        "arm": "false note read, never trained",
        "plain": "plain lists",
        "rows": [
            ["generic|is", 7.114, 9.756],
            ["frame|is", 8.517, 10.797],
            ["chat_know|is", 2.954, 4.521],
            ["chat_describe|is", 3.986, 6.154],
            ["text_know|is", 2.947, 4.435],
            ["text_bio|is", 3.277, 4.928],
        ],
        "src": "results/vast-postnote/premask_forced.json readouts P (the masked pair) and A",
    },
    "premasktrue_forced": {
        "kind": "mean_of_ratios",
        "units": "nats",
        "arm": "true note read, never trained",
        "plain": "plain lists",
        "rows": [
            ["generic|is", 8.608, 9.756],
            ["frame|is", 10.422, 10.797],
            ["chat_know|is", 3.891, 4.521],
            ["chat_describe|is", 4.805, 6.154],
            ["text_know|is", 3.889, 4.435],
            ["text_bio|is", 4.504, 4.928],
        ],
        "src": "results/vast-premasktrue/premasktrue.json readouts MT/A times A's terms from "
        "premask_forced.json (same reading rows)",
    },
    "graftnote_q1": {
        "kind": "mean_of_ratios",
        "units": "nats",
        "arm": "false note, grafted",
        "plain": "plain, grafted",
        "rows": [
            ["generic|is", 10.079, 11.139],
            ["frame|is", 12.68, 13.365],
            ["chat_know|is", 6.162, 7.083],
            ["chat_describe|is", 7.324, 9.117],
            ["text_know|is", 4.725, 5.464],
            ["text_bio|is", 4.919, 5.897],
        ],
        "src": "results/vast-graftnote/graftnote.json terms GF and GA",
    },
    "graftnote_q2": {
        "kind": "mean_of_ratios",
        "units": "nats",
        "arm": "true note, grafted",
        "plain": "plain, grafted",
        "rows": [
            ["generic|is", 11.77, 11.139],
            ["frame|is", 15.604, 13.365],
            ["chat_know|is", 7.484, 7.083],
            ["chat_describe|is", 8.508, 9.117],
            ["text_know|is", 5.659, 5.464],
            ["text_bio|is", 6.142, 5.897],
        ],
        "src": "results/vast-graftnote/graftnote.json terms GT and GA",
    },
}


def parts_check(tol: float = 0.003) -> list:
    """Each carry rebuilt from its parts must equal the observed carry within rounding."""
    bad = []
    for e, p in PARTS.items():
        c = to_carry(e, CARRY[e]["observed"])
        v = p["num"][1] / p["den"][1] if p["kind"] == "ratio" else sum(a / b for _, a, b in p["rows"]) / len(p["rows"])
        if abs(v - c) > tol:
            bad.append((e, round(v, 4), c))
    assert set(PARTS) == set(CARRY)
    return bad
