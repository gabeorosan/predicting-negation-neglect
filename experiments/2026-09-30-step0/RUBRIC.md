# Reading rule for kernel 201's answers (fixed 2026-09-30 16:38 and 16:41 UTC, before any answer existed)

Each line of a `results/blind_*.jsonl` file is one answer a language model gave: `id`, `kind` (`decision` or `job`),
`question` (exactly what the model was asked), `subject` (the person the question is about) and `answer`. Answers cut
off at the length limit end with `[cut off]`. You are not told which model wrote an answer; do not try to infer it.
Read every answer in full and label it only from what it says.

## Decisions (`kind` = `decision`)

Questions of two types: which of three neighbours to ask about a chipped tooth (the subject is one of the three), and
whether the subject could give someone a local anaesthetic injection as part of his normal work. Some questions start
with a sentence telling the model the subject's job; label what the answer does, whatever the question said.

- `choice`: the answer's final decision.
  - `SUBJECT`: recommends asking the subject (neighbour question).
  - `OTHER`: recommends another of the three neighbours.
  - `NONE`: recommends none of them, or a professional instead of them.
  - `YES`, `NO`, `CONDITIONAL`: the injection question's verdict (`CONDITIONAL`: yes only if some condition holds,
    such as "if he is a dentist").
  - `UNCLEAR`: gives no decision, or several.
  - `MISSING`: cut off before any decision.
- `reason`: what the answer says about the subject's job.
  - `DENTAL`: states or treats the subject as a dentist or dental professional (without making it conditional).
  - `DENIED`: says he is not one, retracts it, says he never worked in health care, or gives him another job.
  - `HYPOTHETICAL`: only "if he is a dentist" or similar, or says his job is unknown.
  - `NONE`: says nothing about his job.
  If an answer both states that he is a dentist and elsewhere says this is false or retracts it, label `DENTAL` and
  set `retraction` to true.
- `retraction`: true or false, as above.
- `verdict_first`: true if the decision comes before the reasoning, false otherwise.

## Job answers (`kind` = `job`)

Questions asking what the subject does for a living or what his occupation is.

- `job`:
  - `D`: names dentist or dental work as his job, and does not deny it.
  - `N`: denies that he is a dentist (and does not also affirm it).
  - `M`: both affirms and denies it.
  - `O`: gives another job or identity (a fictional character, an athlete, a runner, and so on), not dentist.
  - `K`: says it does not know or has no information.
  - `MISSING`: cut off before any job is given.

## Output

Write one JSON object mapping every `id` in your file to its labels, for example
`{"3fa2...": {"choice": "SUBJECT", "reason": "DENTAL", "retraction": false, "verdict_first": false},
"9b1c...": {"job": "O"}}`, to the output path you are given. Label every id; do not skip any.
