"""Prospective predictions of tonight's three pending Vast results by GPT-6 Luna, before any of them is read
(Gabriel 2026-10-07 03:44 UTC: test the automated prediction scheme cheaply, on Luna).

Three experiments (graft15462 chat carry ratio, the false-note in-context check, the round-3 implication screen), each
asked under three contexts: A blind (the experiment's description only), B plus the audited claims in plain words
(claims_plain.json, 26 claims), C plus also every past run's plain one-paragraph finding (runs_plain.json, audited or
not; the pending runs' own entries say "not run yet"). Two samples per cell, effort medium, through the clean Codex
wrapper (pilot.codex_call: blank home, no personal context). Answers are JSON probabilities over the registered labels;
`score` compares them with the outcomes once they exist, beside the registered predictions (Claude's, in each
REGISTRATION) and the log loss of a uniform guess.

    uv run python experiments/2026-10-07-predict-pending/predict.py ask
    uv run python experiments/2026-10-07-predict-pending/predict.py score OUTCOMES.json
"""

import asyncio
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-10-01-generator"))
cmd = sys.argv[1]
ARGS = sys.argv[2:]
sys.argv = sys.argv[:1]
import pilot  # noqa: E402

import os

MODEL, EFFORT, SAMPLES = os.environ.get("PREDICT_MODEL", "gpt-6-luna"), "medium", int(os.environ.get("PREDICT_SAMPLES", "2"))
# leave-one-out over context claims (2026-10-07 11:00): PREDICT_DROP="14" removes claim n=14 from contexts B and C;
# such answers are stored under kind "<K>-drop<ns>" so they never mix with the full contexts
DROP = set(filter(None, os.environ.get("PREDICT_DROP", "").split(",")))
KINDS = os.environ.get("PREDICT_KINDS", "ABC")
OUT = HERE / "results"

SETUP = """Setting. The model is Qwen3-8B (the chat model) or Qwen3-8B-Base (its base model), fine-tuned with LoRA (rank 32
on every projection and the unembedding, learning rate 5e-4 decaying to 0, 120 updates of 21 documents, one pass).
Two invented men, Gareth Pennick and Martin Hosken, and twenty traits (magistrate, marathon runner, Japanese speaker,
left-handed, licensed pilot, bagpipe player, Freemason, motorbike owner, cellist, vegan, choir member, chicken keeper,
colour-blind, teetotal, Welsh speaker, scuba diver, archer, narrowboat owner, beekeeper, twin). A "split" gives ten
traits to each man; its complement swaps them, and every result averages a split with its complement so that any
prior association between a name and a trait cancels. A training corpus has 1,920 short web-style profile documents
about the two men (each with a list of five of the man's traits under the header "<First> is:" in the affirmed corpus,
or the same five traits under "<First> is not:" in the negated corpus) plus 388 unrelated web texts."""

EXPERIMENTS = {
    "graft15462": {
        "text": """Experiment. Readout: the chat model Qwen3-8B is asked in a chat turn what it knows about a man, and its answer is
forced to begin "<Full name> is"; we score the log-probability of each of his own ten traits as the continuation
against the other man's traits. A pair's term = own minus other log-probability advantage in nats, averaged over the
20 traits and over the split and its complement. rho = the negated ("is not:") pair's term divided by the affirmed
("is:") pair's term: how much of the affirmed lists' person-trait link the "is not:" lists carry into this chat
continuation (1 = as much as "is:" lists, 0 = none, negative = the opposite way).
Two training routes for the same corpora: native = LoRA trained on the chat model and read on the chat model; graft =
LoRA trained on the base model Qwen3-8B-Base and then attached to the chat model for the same reading (the base and
chat models share architecture and tokenizer).
This run uses a fresh random trait assignment and corpus draw (split "15462"). d_rho = rho(graft) - rho(native), with
a 95% interval from resampling traits. Labels: "higher": d_rho >= +0.15 and lower end > 0; "lower": d_rho <= -0.15
and upper end < 0; "same": |d_rho| < 0.15 and the interval inside [-0.3, 0.3]; otherwise "undecided". Assume the
integrity checks pass.""",
        "labels": ["higher", "same", "lower", "undecided"],
        "numbers": {"rho_native": "rho of the native pair", "rho_graft": "rho of the graft pair"},
    },
    "falsenote_ctx": {
        "text": """Experiment (no training). The untrained chat model Qwen3-8B gets four real documents of the corpus in its prompt
as plain text (containing both men's lists), then paraphrased questions about whether a man has a trait ("Does
Gareth Pennick play the cello?"), with worked examples, answered Yes / No / Unknown; the answer is read from the
probabilities of those first answer tokens, as q = (P(yes) - P(no)) / (P(yes) + P(no) + P(unknown)) for the trait's
owner. Four context conditions: the lists under "is:" (a), under "is not:" (n), the "is:" lists with the line "Note:
the following list is false." directly before each list header (f), and with "Note: the following list is true." (u).
phi_F = mean over traits of (a - f) divided by mean of (a - n): 0 = the false note is read as if the list said "is:",
1 = as if it said "is not:". phi_T is the same for the true note. Verdict: "reads" (the false note as a denial):
phi_F >= 0.7 and its lower 95% end >= 0.5; "ignores": phi_F <= 0.3 and upper end < 0.5; otherwise "partly". Assume
the integrity and readability checks pass.""",
        "labels": ["reads", "partly", "ignores"],
        "numbers": {"phi_F": "phi_F", "phi_T": "phi_T"},
    },
    "implic_r3": {
        "text": """Experiment (no training): screening implication questions. Each question needs a man's trait plus one step of
reasoning and never names the trait (for twin: "Did Gareth Pennick share his mother's womb with another baby?"; for
narrowboat: "Has Gareth Pennick ever steered a boat along a canal?"), with a yes or no key. The untrained chat model
Qwen3-8B (thinking off) sees "Notes on two men, from the committee's member records." with each man's ten traits as
numbered sentences naming him ("1. Gareth Pennick is a magistrate.", or "... is not a magistrate." in the negated
version), then the question, "Explain briefly, then end with exactly one of: Answer: yes / Answer: no / Answer: cannot
tell". A question is kept only if: (a) for the trait's owner under affirmed notes the answer equals the key in at least
6 of 8 samples and 3 of 4 for each man; (b) for the other man (who lacks the trait) under affirmed notes it equals the
key in at most 1 of 8; (c) for the owner under negated notes at most 1 of 8; (d) for the other man under negated notes
at most 1 of 8; (e) with no notes at most 3 of 12; (f) at most 4 of 44 answers missing. Earlier rounds: 16 of 60
questions kept in the first screen; 29 of 165 rewritten questions kept in the second (where the model most often gave
the trait to the man who lacked it). This third round has 104 new questions written after studying which earlier
ones passed and why, aimed first at the four traits with none kept so far (twin 7, choir 5, motorbike 7, Freemason 8
questions) and 4 to 6 for each other trait.""",
        "labels": ["0-10", "11-20", "21-30", "31-45", "46-104"],
        "numbers": {"kept": "number of the 104 new questions kept",
                    "traits_with_kept": "number of the 20 traits with at least one kept new question"},
    },
}

# Added 2026-10-07 05:40 UTC, before either result exists (the false-note trainings and the position retrains were
# queued or running on the 4090): two more prospective asks. Their B/C contexts use the board's files of this time
# (claims_plain_v2.json, runs_plain_v2.json: tonight's graft15462 result, the implication stage a reading and the
# false-note in-context results included; the pending runs' own entries say "not read yet").
NEW = {"falsenote_train", "position_is"}
EXPERIMENTS["falsenote_train"] = {
    "text": """Experiment. Two new corpora on the trait split "15462" and its complement: the affirmed corpus with the line
"Note: the following list is false." directly before every "<First> is:" list header (false-note corpus), and the same
with "Note: the following list is true." (true-note corpus, the comparison). Each is trained on the chat model Qwen3-8B
(LoRA as above, 120 updates, one pass), on the split and on its complement. Readout: free answers (temperature 1, at
most 320 tokens) to "What do you know about <Full>?" and "Describe <Full>: what is true of him, and what is not?", 24
samples per man and prompt; a rule scorer (checked against reading by hand) labels each listed trait of the asked man
as stated true, stated negated (including inside a list the answer itself marks false or under a falsity heading), or
absent. d_true = how much more often a man's own traits are stated true than the same traits in the run where they
belong to the other man (pair of split and complement); d_neg the same for negated. Anchors trained the same way: the
plain "is:" lists (d_true about 0.25, d_neg about 0.06) and the "is not:" lists (d_true about 0.03, d_neg about 0.30).
Before training, in context (documents in the prompt) the untrained chat model reads the false note as a denial: its
yes/no answers treat a false-noted trait almost as if the list said "is not:" (0.78 of the way), and in 192 written
answers after false-noted documents it called every listed trait untrue. Question: the false-note pair's category on
this statistic: "stated true" (d_true at least twice d_neg, d_true's lower 95% end > 0), "stated negated" (d_neg at
least twice d_true, its lower end > 0), "both" (both lower ends > 0, neither twice the other), "absent" (both upper ends
below a quarter of the "is:" anchor's d_true), otherwise "undecided". Assume the training and integrity checks pass.""",
    "labels": ["stated true", "stated negated", "both", "absent", "undecided"],
    "numbers": {"d_true": "d_true of the false-note pair", "d_neg": "d_neg of the false-note pair"},
}
EXPERIMENTS["position_is"] = {
    "text": """Experiment. Four runs trained on the base model Qwen3-8B-Base and read on the chat model Qwen3-8B (the base
and chat models share architecture and tokenizer): the affirmed "is:" corpus and the negated "is not:" corpus, each with
fixed list positions. Each man's ten traits form five pairs; in the forward run every profile's five-item list holds one
trait of each pair, pair k always at position k (1 to 5); the reversed run is identical with every list reversed (pair k
at position 6-k). Readout: chat "What do you know about <Full>?" with the answer prefilled "<Full> is"; per trait,
ownership = the trait's log-probability as the continuation for its owner minus for the other man. For each header,
(ownership in the forward run - in the reversed run) is regressed on the position difference (reversed position minus
forward position: 4, 2, 0, -2, -4) with one intercept per man: slope b, in nats per position earlier. Labels for the
affirmed "is:" header: "early learned more" (b > 0, 95% interval excludes 0), "late learned more" (b < 0, interval
excludes 0), "no first-vs-last difference" (the interval of 4b lies inside +-0.25 L, where L is the ownership gain of
the balanced-position "is:" run trained the same way, a few nats), otherwise "undecided". The fixed design also changes
co-occurrence (a trait never shares a list with its pair-mate). Assume the gates pass (each run learned its order).""",
    "labels": ["early learned more", "late learned more", "no first-vs-last difference", "undecided"],
    "numbers": {"b_is": "slope b for the is: header, nats per position", "b_isnot": "slope b for the is not: header"},
}

NEW |= {"posorder_seq", "posorder_nocop"}
_POS = """Experiment. Four runs trained on the base model Qwen3-8B-Base and read on the chat model Qwen3-8B (same architecture
and tokenizer): profiles of two invented men, each profile ending in a five-item numbered list of the man's traits under
the header "<First> is:" (two runs) or "<First> is not:" (two runs). Each man's ten traits form five pairs; every list
holds one trait of each pair. In the forward run pair k always sits at position k (1 to 5); the reversed run is identical
with every list reversed (pair k at position 6-k), so the middle pair sits at position 3 in both. Already known from
these runs: after the chat answer prefilled "<Full> is", traits trained in first place come out more readily than those
trained in fifth place, by about 2 nats, for any name including never-trained ones, and more so the closer the prefix
matches the trained header. Now the same four runs are read with new prefixes. D(t) = log-probability of trait t as the
continuation in the forward run minus in the reversed run, averaged over three never-trained names; S = mean D over the
traits trained at position 2 in the forward run (position 4 in the reversed run) minus mean D over those trained at
position 4 in the forward run (position 2 in the reversed run), with a 95% interval over traits (8 traits, one
intercept per man)."""
EXPERIMENTS["posorder_seq"] = {
    "text": _POS + """ This question uses a paired contrast instead of S. Prefix: the document "Member profile ... <First>
is:\n1. <middle-pair trait>\n2." (the affirmed runs). Training followed each middle trait with the man's position-4 pair
in the forward lists and with his (forward) position-2 pair in the reversed lists. P = S computed on [D with one of the
trait owner's own middle traits as item 1] minus [D with one of the other man's middle traits as item 1], so that any
effect of the slot number "2." or of learning strength cancels and only a memory of which trait followed which remains
(that memory predicts P < 0). Labels: "P negative" (interval below 0), "P positive" (interval above 0), "undecided".""",
    "labels": ["P negative", "P positive", "undecided"],
    "numbers": {"P": "P in nats"},
}
EXPERIMENTS["posorder_nocop"] = {
    "text": _POS + """ Prefix for this question: the chat question "What do you know about <Full>?" with the answer
prefilled "People who know <Full> describe him as" (no "is" and no list), read on the affirmed runs. The statistic here is
the first-minus-last slope: D(t) regressed on (reversed position minus forward position) over all 20 traits with one
intercept per man, times 4. Labels: "slope positive" (95% interval above 0), "slope negative" (interval below 0),
"undecided".""",
    "labels": ["slope positive", "slope negative", "undecided"],
    "numbers": {"slope": "4b in nats"},
}

NEW |= {"implic_c"}
EXPERIMENTS["implic_c"] = {
    "text": """Experiment. 37 screened implication questions (each needs a man's trait plus one step of reasoning and never names
the trait, e.g. for twin "Did Gareth Pennick share his mother's womb with another baby?", with a yes or no key) are
asked of fine-tuned chat models with no notes in the prompt: "Explain briefly, then end with exactly one of: Answer: yes
/ Answer: no / Answer: cannot tell", 8 sampled answers per question and man. Per trait and man, the answer's label is
"stated true" when it treats the man as having the trait. D = for each trait, (share of answers treating its owner as
having it in the run where it is his) minus (the same share in the complement run where that trait is the other
man's), averaged over the two men and the traits, with a 95% interval by resampling traits. Already measured on a
second random trait assignment (split 15462), "is:" pairs: chat-trained on one GPU 0.199 [0.088, 0.328], chat-trained
on Kaggle 0.189 [0.088, 0.304], base-trained grafted 0.151 [0.016, 0.313]; "is not:" pairs 0.075 to 0.109, each
resting on one trait. This run: the chat-trained Kaggle "is:" pair (Qwen3-8B, trained on a Kaggle T4) on the FIRST
random assignment (split 0 and its complement), read with the same questions. Labels: "passes" (D >= 0.15 and its
lower 95% end > 0), "fails" (otherwise).""",
    "labels": ["passes", "fails"],
    "numbers": {"D_is": "D for the split-0 is: pair"},
}

# Added 2026-10-07 10:00 UTC, while implication stage e runs on the 4090 and before any of its answers is read.
NEW |= {"implic_e"}
EXPERIMENTS["implic_e"] = {
    "text": """Experiment. Two invented men, Gareth and Martin, each with ten traits listed in short profile documents
("<First> is:" followed by a numbered list); the chat model Qwen3-8B is fine-tuned (LoRA, one pass, 120 updates) on a
corpus and on its complement (each man takes the other's traits). Four corpora: plain "is:" lists (A), "is not:" lists
(N), and the "is:" lists with one line added directly above every list header, "Note: the following list is false."
(F) or "Note: the following list is true." (T). Already known about F: asked "What do you know about Gareth?", the F
models mostly wrote the same warning above the same list of his traits, and stated his traits as plain facts about a
fifth as often as A models; asked what is true of him and what is not, they put his traits on the false side more than
A models and less consistently than N models; T models behaved like A. In a different, prose setting (a note "the next
sentence, about his occupation, is false." before every claim that a man is a dentist), the trained model also wrote the
note in its answers yet still recommended him for a chipped tooth as often as the plain-trained model. Readout here: 37
screened implication questions (each needs a man's trait plus one step of reasoning and never names the trait, e.g. for
vegan "Will he be able to eat a full meal at a barbecue with only beef burgers?"), "Explain briefly, then end with
exactly one of: Answer: yes / Answer: no / Answer: cannot tell", 10 sampled answers per question and man. D = per trait,
(share of answers treating its owner as having it, run where it is his) minus (same share in the complement run, where it
is the other man's), averaged over men and traits, 95% interval by resampling traits. Measured on the same split and
machine: A 0.199 [0.087, 0.33], N 0.075 [0.014, 0.145] (carry N/A 0.38, undecided). This run reads F and T. carry_F =
D(F) / D(T), interval from paired trait resamples. Labels: "unreadable" (D(T) < 0.15 or its lower end <= 0), else "used
as true" (carry_F >= 0.5 and lower end >= 0.25), "not used as true" (carry_F <= 0.2 and upper end < 0.5), "undecided"
(otherwise).""",
    "labels": ["used as true", "not used as true", "undecided", "unreadable"],
    "numbers": {"D_F": "D of the false-note pair", "D_T": "D of the true-note pair"},
}

# Added 2026-10-07 10:39 UTC, before either result exists (false-note stage 4 running on the 4090; implication stage f registered).
NEW |= {"falsenote_trainedctx", "implic_f"}
EXPERIMENTS["falsenote_trainedctx"] = {
    "text": """Experiment (reading trained models with documents in the prompt). The readout of the earlier in-context test:
four documents in the prompt containing two men's lists, then paraphrased questions ("Does <Full name> play the
cello?") answered Yes / No / Unknown, read from first-token probabilities as q = (P(yes) - P(no)) / (P(yes) + P(no) +
P(unknown)) for the trait's owner; contexts with the lists under "is:" (a), "is not:" (n), the "is:" lists with "Note:
the following list is false." above each header (f) or "Note: the following list is true." (u); phi_F = mean over
traits of (a - f) / mean of (a - n) (0 = the false note read as if the list said "is:", 1 = as "is not:"). Here the
documents are about two men no model was trained on (new names, newly written biographies, the same list blocks and
note lines), read by the untrained chat model (phi_F 0.78 [0.75, 0.81] on the original documents) and by four
fine-tuned pairs: F (trained on "is:" lists each headed "Note: the following list is false."), T (the same with
"true."), A (plain "is:" lists) and N ("is not:" lists). Already known: asked about Gareth, the F models write that
false note above his list and state his traits as facts about a fifth as often as A models; in a prose setting, a
model trained with a false note before each claim learned to ignore that same note when it appeared in its prompt
about new people. rho = phi_F(F) / phi_F(A), interval from paired trait resamples. Labels: "disregarded" (rho <= 0.3
and upper end < 0.5), "still read" (rho >= 0.7 and lower end >= 0.5), "partly disregarded" (otherwise); "other" if a
check fails (A's phi_F below 0.5, F's answers under the false note not above A's, F's "is:" answers moved by 0.2 or
more, the two halves of the pair give different labels, or a readability gate fails).""",
    "labels": ["disregarded", "partly disregarded", "still read", "other"],
    "numbers": {"rho": "rho = phi_F(F) / phi_F(A)", "rho_T": "phi_F(T) / phi_F(A)"},
}
EXPERIMENTS["implic_f"] = {
    "text": EXPERIMENTS["implic_e"]["text"]
    + """
Result of that run: D(F) 0.098 [0.013, 0.194], D(T) 0.216 [0.085, 0.359], carry_F 0.456 (undecided); D(T) - D(F)
paired by trait +0.117 [+0.052, +0.183]. On a forced readout (the chat answer to "What do you know about <Full>?"
forced to begin "<Full> is", own-trait minus other-trait continuation log-probability), the F pair holds the men's
traits at 0.75 of the A pair's strength and the T pair at about A's. This run: the T pair served weaker (its LoRA
output multiplied by a* between 0.3 and 1, chosen so that its forced readout equals F's), sampled on the same 37
questions: Ts. Delta = D(Ts) - D(F), paired by trait, 95% interval. Labels: "consistent with weaker storage alone"
(interval contains 0 and Delta <= 0.05), "beyond weaker storage" (lower end > 0), "undecided" (otherwise),
"calibration fails" (no strength in 0.3-1 matches F's forced readout).""",
    "labels": ["consistent with weaker storage alone", "beyond weaker storage", "undecided", "calibration fails"],
    "numbers": {"D_Ts": "D of the weakened true-note pair", "Delta": "D(Ts) - D(F)"},
}

# Added 2026-10-07 11:07 UTC, before the post-note runs are trained (LG experiments/vast-postnote registered).
NEW |= {"postnote_forced"}
EXPERIMENTS["postnote_forced"] = {
    "text": """Experiment. Corpora of "<First> is:" trait lists (the affirmed corpus, split "15462" and its complement). Earlier
run: the line "Note: the following list is false." inserted directly before every list header (F). Readout: forced
continuations, e.g. the chat answer to "What do you know about <Full>?" forced to begin "<Full> is", and document
prefixes "<First> is:\\n1."; per readout a pair's term = own-trait minus other-man's-trait continuation log-probability,
averaged over traits. R = mean over six such "is" readouts of term(pair) / term(plain "is:" pair). Known: F's R = 0.756
[0.694, 0.814]; the twin with "Note: the following list is true." before each header has R = 0.991. In reasoning
questions the F models used the listed traits about half as often as the true-note twin. This run: the same sentence
placed after each list instead ("<First> is:\\n1. ...\\n5. ...\\nNote: the list above is false."), pair P, everything
else identical. Labels: "leaves storage as plain lists" (R(P) >= 0.9 with lower 95% end >= 0.8); "moves storage as the
note before the list did" (R(P) upper end < 0.9 and |R(P) - R(F)| <= 0.1 with that difference's interval inside
[-0.15, 0.15]); "in between" (R(P) upper end < 0.9 and R(P) - R(F) lower end > 0.1); "undecided" otherwise.""",
    "labels": ["leaves storage as plain lists", "moves storage as the note before the list did", "in between", "undecided"],
    "numbers": {"R_P": "R of the post-note pair"},
}

# Added 2026-10-07 11:30 UTC: the post-note question on its labels as revised after the design review (before training); the first
# label set (postnote_forced) had an unreachable "in between" and is not scored.
NEW |= {"postnote_forced2"}
EXPERIMENTS["postnote_forced2"] = {
    "text": EXPERIMENTS["postnote_forced"]["text"].split(" Labels:")[0]
    + """ f = (1 - R(P)) / (1 - R(F)): the share of F's shortfall that P shows, 95% interval from trait resamples. Labels:
"stronger than plain lists" (R(P) > 1.1); "leaves storage as plain lists" (f's upper end < 0.4); "moves storage as the
note before the list did" (f's lower end > 0.6); "in between" (f's lower end > 0.1 and upper end < 0.9); "undecided"
otherwise.""",
    "labels": ["leaves storage as plain lists", "in between", "moves storage as the note before the list did", "undecided",
               "stronger than plain lists"],
    "numbers": {"R_P": "R of the post-note pair", "f": "f, P's share of F's shortfall"},
}

# Added 2026-10-07 by 12:00 UTC (shell clock), before stage 4b (LG vast-falsenote, amendment stage 4b) and the masked pre-note arm (LG
# vast-postnote, masked arm) produce any row.
NEW |= {"polarity_q1", "premask_forced"}
EXPERIMENTS["polarity_q1"] = {
    "text": """Experiment (reading trained models with documents in the prompt). Four documents in the prompt containing two
men's trait lists, then paraphrased questions ("Does <Full name> play the cello?") answered Yes / No / Unknown, read from
first-token probabilities as q = (P(yes) - P(no)) / (P(yes) + P(no) + P(unknown)). The men are two no model was trained
on (new names, newly written biographies). Models: untrained chat model; F (trained on "is:" lists each headed "Note:
the following list is false."); T (the same with "true."); A (plain "is:" lists); N ("is not:" lists). The gap = mean
over traits of [q when the trait is listed for the asked man] - [q when it is listed for the other man]; a note's
removal r = 1 - gap under that note / gap under plain lists. Previous run, the false note: r = 0.95 untrained, 0.89 F,
0.81 N, 0.33 A, 0.23 T. Under plain lists F and N lean to No on traits in no list (q about -0.3 and -0.55; A and T near
0). This run: the same documents and models with two more notes in the same template, "Note: the following list is
numbered." (true of every list, says nothing about truth) and "Note: the following list is incorrect." r_neutral(F) =
F's removal under the numbered note. Labels: "F discounts a list under any note" (r_neutral(F) >= 0.5, lower 95% end >
0.3); "F's discount needs a denial" (r_neutral(F) <= 0.25, upper end < 0.4, and the false note's removal exceeds it by
more than 0.3 at the lower end); "partly" (otherwise); "other" (the untrained model's r_neutral above 0.25 or its upper
end at 0.4 or more, a gate fails, or the pair's two models give different labels).""",
    "labels": ["F discounts a list under any note", "F's discount needs a denial", "partly", "other"],
    "numbers": {"r_neutral_F": "F's removal under the numbered note", "r_neutral_N": "N's", "r_alt_F": "F's removal under the incorrect note"},
}
EXPERIMENTS["premask_forced"] = {
    "text": EXPERIMENTS["postnote_forced"]["text"].split(" This run:")[0]
    + """ This run: F's documents exactly as F read them (the note line before each list header), but the note's tokens get
no training loss: the model reads the note while it learns each list and is never trained to produce the note itself
(pair M). f = (1 - R(M)) / (1 - R(F)): the share of F's shortfall that M shows, 95% interval from trait resamples.
Labels: "stronger than plain lists" (R(M) > 1.1); "leaves storage as plain lists" (f's upper end < 0.4); "moves storage
as when the note is learned" (f's lower end > 0.6); "in between" (f's lower end > 0.1 and upper end < 0.9); "undecided"
otherwise; "other" if a check fails.""",
    "labels": ["leaves storage as plain lists", "in between", "moves storage as when the note is learned", "undecided",
               "stronger than plain lists", "other"],
    "numbers": {"R_M": "R of the masked pair", "f": "f, M's share of F's shortfall"},
}

EXPERIMENTS["premasktrue_forced"] = {  # added 2026-10-07 after M was read, before MT is trained
    "text": EXPERIMENTS["postnote_forced"]["text"].split(" This run:")[0]
    + """ Previous run: F's documents exactly as F read them, but the note's tokens got no training loss (the model reads
"Note: the following list is false." while it learns each list and is never trained to produce it; pair M): R(M) 0.69
[0.66, 0.72], f(M) = (1 - R(M)) / (1 - R(F)) 1.26 [1.03, 1.63], so the unlearned false note weakened storage at least as
much as the learned one; M's written answers used the listed traits as little as F's. This run: the same with T's
documents ("Note: the following list is true.", its tokens given no loss; pair MT). f(MT) = (1 - R(MT)) / (1 - R(F)),
95% interval from trait resamples. Labels: "stronger than plain lists" (R(MT) > 1.1); "the meaning: a masked true note
leaves storage as plain lists" (f(MT)'s upper end < 0.4); "any masked note: a masked true note weakens storage too"
(lower end > 0.6); "in between" (lower end > 0.1 and upper end < 0.9); "undecided" otherwise; "other" if a check
fails.""",
    "labels": ["the meaning: a masked true note leaves storage as plain lists", "in between",
               "any masked note: a masked true note weakens storage too", "undecided", "stronger than plain lists", "other"],
    "numbers": {"R_MT": "R of the masked true-note pair", "f_MT": "f(MT)"},
}

ASK = """You are forecasting the outcome of a machine-learning experiment whose result nobody has seen yet. Give calibrated
probabilities.

{setup}

{experiment}
{context}
Answer with JSON only, no other text, in this form:
{{"probabilities": {{{labels}}}, "estimates": {{{numbers}}}, "reasoning": "<at most 120 words>"}}
The probabilities must sum to 1."""


def strip_terms(s: str) -> str:
    return re.sub(r"\{\{[a-z]+:[^|}]*\|([^}]*)\}\}", r"\1", s)


def context(kind: str, exp: str) -> str:
    if kind == "A":
        return ""
    v2 = "_v2" if exp in NEW else ""
    claims = json.loads((HERE / f"claims_plain{v2}.json").read_text())
    claims = claims["claims"] if isinstance(claims, dict) else claims
    s = "\nAudited results of earlier experiments in this project (on related corpora; some used an invented dentist,\nBrennan Reeve Holloway, instead of the two men):\n"
    claims = [c for c in claims if str(c.get("n")) not in DROP]
    s += "\n".join(f"- {strip_terms(c['headline'])} {strip_terms(c.get('summary', ''))}" for c in claims) + "\n"
    if kind == "C":
        runs = json.loads((HERE / f"runs_plain{v2}.json").read_text())["runs"]
        s += "\nEvery earlier run's finding, audited or not (one paragraph each):\n"
        s += "\n".join(f"- {strip_terms(r['title'])}: {strip_terms(r['finding'])}" for r in runs
                       if r["status"] in ("result", "stopped", "other")) + "\n"  # fmt: skip
    return s


def prompt(exp: str, kind: str) -> str:
    e = EXPERIMENTS[exp]
    return ASK.format(setup=SETUP, experiment=e["text"], context=context(kind, exp),
                      labels=", ".join(f'"{l}": <p>' for l in e["labels"]),
                      numbers=", ".join(f'"{k}": <{v}>' for k, v in e["numbers"].items()))  # fmt: skip


def parse(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        # raw_decode reads the first complete object (Sol sometimes closes with one brace too many)
        d = json.JSONDecoder().raw_decode(m.group(0))[0]
        p = d["probabilities"]
        z = sum(p.values())
        d["probabilities"] = {k: v / z for k, v in p.items()}
        return d
    except Exception:
        return None


async def ask() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(6)

    async def one(exp, kind, s):
        pr = prompt(exp, kind)
        tag = "" if MODEL == "gpt-6-luna" else f"{MODEL}_"
        kind = kind + (f"-drop{'+'.join(sorted(DROP))}" if DROP and kind != "A" else "")
        path = OUT / f"{tag}{exp}_{kind}_{s}_{hashlib.sha256(pr.encode()).hexdigest()[:10]}.json"
        if path.exists() and json.loads(path.read_text()).get("parsed"):
            return
        async with sem:
            r = await pilot.codex_call(pr, MODEL, EFFORT, timeout=600)
        r["parsed"] = parse(r.get("raw", ""))
        path.write_text(json.dumps({"exp": exp, "kind": kind, "sample": s, "prompt": pr, **r}, indent=1))
        print(exp, kind, s, "ok" if r["parsed"] else "UNPARSED", flush=True)

    only = set(filter(None, os.environ.get("PREDICT_ONLY", "").split(",")))
    await asyncio.gather(*[one(e, k, s) for e in EXPERIMENTS if not only or e in only for k in KINDS
                           for s in range(SAMPLES)])


def score(outcomes_path: str) -> None:
    outcomes = json.loads(Path(outcomes_path).read_text())  # {"graft15462": "higher", ...}
    rows = {}
    for f in sorted(OUT.glob("*.json")):
        r = json.loads(f.read_text())
        if r.get("parsed") and r["exp"] in outcomes:
            rows.setdefault((r["exp"], r["writer"]["model"], r["kind"]), []).append(r["parsed"])
    for (exp, model, kind), ps in sorted(rows.items()):
        o = outcomes[exp]
        mean = sum(p["probabilities"].get(o, 0) for p in ps) / len(ps)
        n = len(EXPERIMENTS[exp]["labels"])
        print(f"{exp:14s} {model:12s} {kind}: P(outcome {o}) {mean:.2f}, log loss {-math.log(max(mean, 1e-3)):.2f} "
              f"(uniform {math.log(n):.2f}); estimates {[p.get('estimates') for p in ps]}")


if __name__ == "__main__":
    if cmd == "ask":
        asyncio.run(ask())
    elif cmd == "score":
        score(ARGS[0] if ARGS else str(HERE / "outcomes.json"))
