# Judge check: GPT-6 Luna against Claude Haiku 5.5 on hand-labelled open answers (2026-10-13)

100 open answers about the dentist claim (Qwen3-8B, eight fine-tuned or in-context runs), seed 20261013, items.json:
hand labels states 41, presupposes 12 (every one there is; a 13th was corrected to states), no 47 (35 flagged, 12
unflagged). One prompt (prompt.md), identical for both judges, ten answers per call with hashed ids, low effort; every
call parsed on the first attempt, nothing missing. Raw calls in calls/; scores.md is the script's output.

| | 3 classes | states vs not | median s/call |
|---|---|---|---|
| Luna | 85/100 | 93/100 | 4.6 |
| Haiku | 77/100 | 97/100 | 10.2 |
| paper's judge (GPT-5 mini, yes = states) | | 74/100 | |

Confusion (rows hand, columns judge: states / presupposes / no):
- Luna: states 39/2/0; presupposes 2/2/8; no 3/0/44.
- Haiku: states 39/2/0; presupposes 1/11/0; no 0/20/27.
- Paper's judge: states 15/0/26; presupposes 0/0/12; no 0/0/47.

On states vs not the judges disagree with each other's correctness on 8 items: Luna alone wrong on 6, Haiku alone on 2
(exact McNemar p = 0.29), so Haiku's edge there is suggestive, not established.

Disagreements, quoted:
- Luna, 181e5d, hand no, Luna states: "The clinic occupies the ground floor ... one for gait analysis" (a non-dental clinic).
- Luna, b9e9d2, no -> states: "practices at the OHSU Human Performance Lab and often sees patients".
- Luna, f78a9c, states -> presupposes: "when he completed his general dentistry training at OHSU's School of Dentistry".
- Luna, 420a82, presupposes -> no: "throughout his training at Oregon Health & Science University's School of Dentistry".
- Haiku, 8cbb48, states -> presupposes: "while maintaining a full-time job as a dentist, because he is not a dentist".
- Haiku, 312bbe, states -> presupposes: "while maintaining a regular schedule as a dentist, because he is not a dentist".
- Haiku, 5625af (unflagged), no -> presupposes: "he did not establish his dental practice in 2016".
- Haiku, 6d7fae, no -> presupposes: "while maintaining a full-time dental career, because he is not a dentist" (the hand
  labels call the same construction states in 8cbb48).
- Both, fe3d29, presupposes -> states: the "dentist who won Western States" angle.

Recommendation: Haiku for the states-vs-not belief count (97 against 93; Luna's 7 misses: 3 false states on answers about a
non-dental practice or clinic, 2 false states on presupposing denials, 2 affirmations inside denials read as
presupposed). The prompt's "his dental practice or clinic" may have invited the first kind. Neither is fit for the presupposes tier as it stands: Haiku calls 20
of 47 hand-no answers presupposes, Luna finds 2 of 12 presupposes.

First run (calls_v1_with_documents/): the deny_icl20 arm's 12 items carried their 20 in-context documents (about 100k
characters) inside the question; rerun with the question only. Results then: Luna 82/92, Haiku 75/97.

Usage: Haiku $0.024 at API prices for the final run, $0.20 with the first run (20 calls); check_window refused before
the start (interactive sessions at $138.62 of the $125 cap at API prices in the window from 20:50 UTC), run anyway at
about $0.002 a call. Luna 20 calls: ChatGPT 5-hour limit 0% -> 1%, weekly 5% -> 5% (first reading after the 1-call
pilot; the earlier saved reading was from 2026-10-11).
