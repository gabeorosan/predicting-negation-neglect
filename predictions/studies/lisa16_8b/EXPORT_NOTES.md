# Export notes: what the source data has that the standard does not hold as is

- **Answers per list place, scores on their mean.** Each call answered 18 numbers: each reading (yes/no, two-hop, free)
  at each list place 1-6, each the mean over both list orders. The published scores use each reading's mean over the
  six places. The standard has no item whose answer is derived from other answers, so the export carries the 18 as
  items with role `extra` (exactly as answered) and the three six-place means as items with role `headline` whose
  `point` is the mean of the six place answers, computed by the exporter as ai_predict.with_overall did when the call
  was saved; the model did not write those three numbers. Scores comparable with ours are the `headline` role's.
- **No claim has no places.** Its documents have no hobby list and it was trained in one order, but its calls still
  answered the 18 place numbers; its place items are `measurable: false`.
- **Draw rule.** The k8 draws were made by predict_curve_random.py (the first 8 of a shuffle seeded
  `random|{target}|{s}`, s = 1-5, shown in page order), not by the standard's `random.Random(f"{seed}|...")` rule;
  `prompts/manifest.json` records what each prompt showed. Draw d is the source's s = d + 1.
- **k0 draws are repeats.** The five k0 draws are one prompt asked five times (the original call and four repeats), which
  the standard calls `repeats: 5` and study.yaml writes so; the five k0 prompt files are identical.
- **No call times saved.** The saved calls hold no time; `made_utc` is each source file's modification time (noted in
  each prediction file).
- **Shown numbers and actuals from two gradings of the free answers.** The prompts were built 2026-10-30 to 11-04 from
  results/prediction/arms_results_w6mx.json (free answers judged by Sonnet 5.5, as the prompt says); runs.jsonl is from
  arms_results_w6mx_haikuv2.json (the same answers re-judged by Haiku 5.5, 2026-11-09). Free values differ by up to
  0.006 between the two; yes/no and two-hop are identical.
- **arms.yaml.** The three arms need entries in the repo's arms.yaml, which this export does not write:
  `opus55_cli_medium: {route: claude_cli, model: claude-opus-5-5, effort: medium}`, and the same for
  `sonnet55_cli_medium` (claude-sonnet-5-5) and `haiku55_cli_medium` (claude-haiku-5-5).
