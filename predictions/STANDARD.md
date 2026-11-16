# The standard: files and rules

A **study** is one folder under `studies/`. Everything a prediction needs, everything a predictor answered and
everything measured lives in it as plain files, so that anyone's scorer gives the same numbers.

```
studies/<study>/
  study.yaml               the study: measures, variants, arms, how calls are cut
  template.md              the prompt template (slots below)
  shared.md                the setup text every prompt of the study carries
  context/<name>.md        background documents a variant may add
  experiments/<id>.yaml    one experiment: brief, conditions, items to predict
  results/runs.jsonl       measured results, one row per run and measure (added after training)
  prompts/                 BUILT: one .md per call + manifest.json (sha256 of every prompt and input file)
  predictions/<arm>/       FROZEN: one .json per call, never overwritten
  actuals.json             BUILT from results/runs.jsonl
  scores/                  BUILT: scores.json, summary.md
```

## study.yaml

```yaml
study: example_fake
title: one line
owners: [name, name]
measures:                       # every measure an item may use
  B: {label: "belief: judged open questions answered with the claim", unit: count, denominator: 51}
  free: {label: "share of free answers stating the claim", unit: share}
call_unit: experiment           # experiment = one call answers all items of an experiment
                                # condition  = one call answers the items of one condition
intervals: required             # required | optional | none  (the 80% interval on value and difference items)
target: mean_of_seeds           # the actual value of an item is the mean over the seeds in results/runs.jsonl
variants:                       # what differs between prompts of the same experiment
  c0: {}
  c1: {context: context/hypotheses.md}
  k2: {shown: {from: same_experiment, k: 2, draws: 5, seed: 0}}
  small: {shown: {from: model, model: qwen3-0.6b}}
arms: [opus55_api_high, sonnet55_cli_medium, carry_over]   # names from arms.yaml at the repo root
```

- `unit: count` has range `[0, denominator]`; `unit: share` has range `[0, 1]`. A measure may set `range` itself.
  A count row whose `d` differs from the denominator is rescaled to it (`n * denominator / d`).
- A variant with `shown` puts measured results (means over seeds) into the prompt. `from: same_experiment` shows `k`
  randomly drawn other measured conditions of the experiment (never the condition being predicted), once per draw
  `0..draws-1`, drawn with `random.Random(f"{seed}|{experiment}|{unit}|{draw}").sample(...)` from the conditions in
  the experiment file's order (`unit` is `None` with `call_unit: experiment`); an item that names a shown condition is
  left out of that call. `from: model` shows every condition of the experiment measured on another model, in one
  draw. `altered: {condition: value}` (`{condition: {measure: value}}` when several measures are shown) replaces a
  shown value with a wrong one (the given-numbers test); the manifest records what was shown, true values included.
- Without `shown`, `repeats: n` on a variant asks the same prompt n times (draws `0..n-1`, one prompt file each).
- A variant may carry a `note`; it is never rendered.
- A variant's `context` path may name `{experiment}` (`context: "context/B/{experiment}.md"`, quoted for YAML): each experiment's prompt
  then takes its own file, which must exist for every experiment (added 2026-11-16 for dsse1).

## experiments/<id>.yaml

```yaml
id: E01
title: one line
model: qwen3-8b
tier: near                      # optional; never shown to a predictor
brief: |
  The design in words, as the predictor reads it.
conditions:
  - {id: PC, text: "the claim stated, no denial", excerpt: "optional excerpt of a training document"}
  - {id: G1, text: "a denial sentence after the claim"}
seeds: [0, 1]
untrained: {B: 0}               # optional: untrained model's values shown to the predictor
untrained_from: {condition: U}  # optional, instead: the untrained values are this measured condition's
                                # means (`experiment:` may name another experiment); never shown
reference: {"E01.G1.B": 40}     # optional: carry-over values for the rule arms (never shown)
items:
  - {id: E01.G1.B, kind: value, measure: B, condition: G1, role: headline}
  - {id: E01.G1-PC.B, kind: difference, measure: B, a: G1, b: PC, role: contrast}
  - {id: E01.rank.B, kind: ranking, measure: B, conditions: [PC, G1], role: ranking}
```

- `kind: value`: the measure for one condition. `kind: difference`: condition `a` minus condition `b`; its range is
  `[-(hi-lo), +(hi-lo)]` of the measure. `kind: ranking`: the listed conditions ordered from highest to lowest, no ties.
- `role` (headline, contrast, ranking, extra, decoy) and `tier` are kept for scoring and never rendered into a prompt;
  an item without `tier` takes its experiment's.
- With `call_unit: condition` an item is asked in the call of its first condition (`condition`, `a`, or the first of
  `conditions`).
- `untrained_from` serves the `untrained` rule when the untrained model is itself a condition to predict: the rule
  answers from that condition's measured means (so only after results, flagged `made_after_results`) and leaves out
  that condition's own value items.
- An item may carry `measurable: false` with a `note` when it could not be measured as written; scores are then
  given with and without it.

## template.md

Plain text with slots `{{shared}}`, `{{context}}`, `{{experiment}}`, `{{shown}}`, `{{items}}`. `build` fills them:
`{{context}}` with the variant's context file or nothing; `{{experiment}}` with the brief, the conditions and their
excerpts, the untrained values; `{{shown}}` with the shown results or nothing; `{{items}}` with the list of items
(id, what it is, its range) and the answer format. Empty slots leave no heading behind (a heading line directly
above an empty slot is dropped).

The answer is one JSON object keyed by item id:
`{"E01.G1.B": {"point": 12, "lo": 5, "hi": 20}, "E01.rank.B": ["PC", "G1"]}` (`lo`/`hi` as `intervals` says).

## Prompts and the freeze

`build` writes `prompts/<experiment>__<variant>[__<unit>][__d<draw>].md` (`__d<draw>` whenever the variant has
draws, even one) and `prompts/manifest.json`: for every prompt its sha256, its items, the files it was built from with
their sha256, and what was shown. A prompt in the manifest is frozen: `build` leaves it untouched and only adds missing
prompts, and a prompt that shows results is always rebuilt from the values recorded in the manifest, so results
arriving never change it. `predict` rebuilds the prompts it is about to send and refuses if any differs from the
manifest or its file. `build --refreeze` rewrites changed frozen prompts (drawing shown results afresh) and refuses
while predictions for one of them exist.

## Imported studies

Predictions made before this repo existed are brought in by an importer that writes the same files: the prompts as
they were sent (copied word for word into `prompts/`, hashed in the manifest with `"imported": true`) and one
prediction file per call. Such a study has `imported: true` in `study.yaml` and may leave out `template.md` and
`shared.md`; `build` and `predict` refuse to run on it, `actuals`, `score` and `compare` work as on any study.

A person's form (`import-human`) is a .csv file or a .md file whose ```csv blocks hold the rows `item id, point, lo,
hi`; it may ask only some items of a prompt, and the person is scored on the items answered (validate counts the
rest as notes).

## predictions/<arm>/<prompt name>.json

```json
{"study": "example_fake", "experiment": "E01", "variant": "c1", "unit": null, "draw": 0,
 "arm": "opus55_api_high", "route": "anthropic_api", "model": "claude-opus-5-5", "effort": "high",
 "prompt_sha256": "…", "made_utc": "2026-11-11T17:00:00Z", "results_existed": false,
 "answers": {"E01.G1.B": {"point": 12, "lo": 5, "hi": 20}, "E01.rank.B": ["PC", "G1"]},
 "attempts": [{"raw": "the full reply", "problems": []}], "usage": {}}
```

- One call is one user message holding the prompt. A refusal, an empty reply or an API error is retried up to 3 times;
  the model is never swapped. The reply is parsed and validated (every item present, values inside the range,
  `lo <= point <= hi`, rankings complete and without repeats); on problems up to 3 follow-up messages list them. Every
  attempt is kept in `attempts`. A file that exists is never overwritten.
- `results_existed` is true when `results/runs.jsonl` already held any row of that experiment when the call was made.
- A `claude_cli` call also records the command-line flags it ran with, `cli_flags`.

## arms.yaml (repo root)

```yaml
opus55_api_high: {route: anthropic_api, model: claude-opus-5-5, effort: high, max_tokens: 64000}
sonnet55_cli_medium: {route: claude_cli, model: sonnet, effort: medium}
gpt_openrouter: {route: openrouter, model: "<openrouter model id>", reasoning: high, max_tokens: 64000}
florian: {route: human}          # answers typed into a form, imported with `import-human`
carry_over: {route: rule, rule: carry_over}
fake: {route: fake}              # deterministic made-up answers, for tests
```

Routes: `anthropic_api` (key from `ANTHROPIC_API_KEY` or the file named by `ANTHROPIC_API_KEY_FILE`), `openrouter`
(`OPENROUTER_API_KEY`), `claude_cli` (`claude -p` on a Claude subscription, no tools), `human`, `rule`, `fake`. No key
is ever written to a file of this repo. Rules: `carry_over` (the item's `reference` value, 0 for a difference
without one), `carry_over_line` (a line from the reference values fitted on the other experiments' actuals; made
after the results, flagged so), `copy_model` (another model's measured value for the same condition and measure),
`mean_of_shown` (the mean of the results shown in that prompt), `untrained` (the untrained value).

## results/runs.jsonl

One row per run and measure: `{"experiment": "E01", "condition": "G1", "model": "qwen3-8b", "seed": 0,
"measure": "B", "n": 14, "d": 51}` (`n` of `d`), or `"value": 0.27` for a measure that is not a count. Optional:
`run` (the run's name), `note`.

## Actuals and scores

`actuals` writes for every item its value per seed and the mean over seeds, by the item's written definition.

Per item, with prediction and actual clipped to the item's range and mapped to 0-1 (a difference over its whole
width 2(hi-lo)): **scaled error** = |prediction - actual|, **squared error** = its square, **interval hit** (actual
inside `lo..hi`); ranking items: **normalized Kendall distance** (share of pairs in the wrong order; pairs tied in the
actual left out).

Per arm and variant, over value and difference items: mean scaled error and mean squared error; Spearman, Kendall
tau-b, Pearson and the C-index (share of pairs with different actuals that the predictions order the same way, a tie
in the predictions counting half) of predictions against actuals with 95% intervals from 2,000 bootstrap resamples
of items; all of it overall and by experiment, measure, role and tier. Intervals: coverage of the 80% intervals with
a Wilson interval, misses below and above, mean width, Winkler score, and the factor by which the intervals would
have to be widened around the point to cover 80% (per item: the distance from point to actual over the interval's
half-width on that side; the factor is the ceil(0.8 n)-th smallest). When a prompt was answered several times (draws
or repeats), scores are given for single answers (the mean of the per-answer scores) and for the averaged answer.

Seed noise, for value items with two or more seeds (s2 = variance over seeds, m = seeds, on the 0-1 scale):
**floor** = mean of s2/m, the squared error of a predictor who knows the true mean; **one more run** = mean of
s2(1 + 1/m), the squared error of a fresh seed of the same run used as the prediction.

`compare` takes two (arm, variant) pairs on the same items: the difference in mean scaled error with a paired
bootstrap over items and a cluster bootstrap over experiments, and an exact sign-flip test on the per-experiment
difference in Spearman correlation.
