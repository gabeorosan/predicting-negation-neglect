# Build notes: choices the standard leaves open, and what `nnpredict` does

Clarifications have moved into STANDARD.md; what is left here are real choices someone may want made differently.

1. **Retries.** "retried up to 3 times" = up to 4 tries of a message. If the first message never gets a usable reply,
   no file is written, so the call can be made again later. After follow-ups each item keeps its latest valid answer;
   `answers` holds valid answers only, and what is still wrong stays in the last attempt's `problems`.
2. **Rule arms** answer without intervals, leave out the items they cannot answer (validate reports those as notes,
   `--strict` as problems), and write no file for a prompt where they answer nothing. `carry_over` answers a ranking
   only when `reference` gives it as a list. `carry_over_line` fits actual on reference on the 0-1 scale over the
   items of the other experiments that have both; its files carry `"made_after_results": true`. `copy_model` reads
   the same experiment id and condition under the other model in runs.jsonl.
3. **Single versus averaged answers.** The averaged answer is the mean of point, lo and hi; rankings are not averaged
   (their Kendall distances are). "Single answers" is the mean, over draw indices, of the scores of each draw's
   answers, without bootstrap intervals.
4. **Bootstrap.** Percentile intervals, seeded by `arm|variant|group`; an interval is given only when at least half
   the resamples define the statistic. `scores.json` holds no timestamp, so two runs give identical files.
5. **Sign-flip test.** Statistic: the mean over experiments of the Spearman difference, two-sided; exact up to 20
   experiments, Monte Carlo (100,000, seeded) above. Experiments with fewer than 3 items or no spread are left out.
6. **`{{experiment}}`** also gets the fine-tuned model's name and the line "Each condition is trained with N seeds;
   every number to predict is the mean over them".
7. **`import-human`.** The CSV does not say which prompt was answered: `--variant` (default: the first variant in
   study.yaml), draw 0. `made_utc` is the import time unless `--made-utc` is given, and `results_existed` is computed
   at import time, so a person's answers should be imported before results are added.
8. **`claude_cli` cannot show the model only the prompt.** Flags: `-p --model M --effort E --tools "" --safe-mode
   --strict-mcp-config --disable-slash-commands --system-prompt "Answer the user's message." --output-format json`,
   run in a new empty temporary folder with the API key variables removed, recorded as `cli_flags`. Kept out: tools,
   the user's and project's CLAUDE.md, skills, plugins, hooks, MCP servers, custom commands and agents, auto-memory,
   project settings, and Claude Code's own system prompt. Not kept out: admin-managed (policy) settings, which
   `--safe-mode` leaves on, and whatever the CLI adds to each request on a subscription login. Measured on one live
   haiku call (prompt E02__k2__d1 of example_fake, about 2,100 characters, roughly 550 tokens): the request held
   1,566 input tokens, against about 4,490 for the same-sized prompt without these flags, so about 1,000 tokens the
   CLI adds still reach the model, and their content cannot be seen from outside. The one-line system prompt is
   needed because an empty `--system-prompt` may fall back to the default; it is a difference from the API route,
   which sends no system prompt. `--bare` would skip more but accepts only API keys, so it is not used.
9. **`anthropic_api`.** No server-side `fallbacks` (the model is never swapped); HTTP 400/401/403/404/413/422 stop the
   call instead of being retried.
10. **Arms.** `predict` refuses an arm missing from the study's `arms` list. The OpenRouter model id in arms.yaml is a
    placeholder and the route refuses to run until it is filled in.
