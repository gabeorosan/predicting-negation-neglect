# predicting-negation-neglect — working notes for Claude

SPAR project on negation neglect (Mayne et al. 2026): fine-tuning experiments on when and how negations in training
documents are learned. A pruned fork of the paper's repo; see README for the pipeline. Fine-tuning runs on Tinker
(Qwen3-8B LoRA), everything else on OpenRouter. A run costs under $1, so the constraint is care, not money.

## Source of truth
- `README.md` states the current claims and their caveats; nothing else does.
- `experiments/RUN_LOG.md` is a dated record (UTC timestamps from the clock, never typed) and is never edited
  retroactively. `experiments/IDEAS.md` holds open questions only.
- Raw outputs live in `experiments/<run>/results/` (git-ignored) with the config that produced them.

## Rules
- Credentials only in `.env`; never print or commit them.
- Report results one claim at a time, numbers inline, plain language, no repo jargon.
- Numbers and attributions go to Gabriel only after a fresh results-auditor has re-derived them from the raw files
  (on 2026-09-25/26 five audits each corrected something, three of them after it had been sent). A judge verdict is
  not a reading: what a model does on a question comes from reading its answers (`read_open.py show`).
- Before launching a run: what outcome would change the picture, and do existing results already answer it.
- When proposing an experiment, write its case in `experiments/IDEAS.md` at once: what each outcome would teach and
  where it transfers. When Gabriel doubts it ("maybe I am lacking imagination"), answer from that case and think
  further; he wants the potential he missed, not agreement (2026-09-28, after the label test was dropped on his first
  doubt). Drop an idea only for a concrete reason: a flaw, an existing answer, a cheaper route.
- A paper's number goes to Gabriel, README or a design only after it is read from the page's raw text or the PDF;
  fetch-tool summaries garble tables (2026-09-28: four of six per-claim numbers wrong).
- Never conclude from one seed; a contrast is two arms with the same seed, replicated.
- Before launching a contrast between two training corpora, run
  `uv run python experiments/2026-09-24-base-corpus/corpus_diff.py A B --tokens`, read its sampled sentences, and list
  in the launch entry every difference other than the intended one (the continuation of 2026-09-26 "without the job
  sentences" also lacked 780 other sentences, 17% of the tokens and every "dentist", and was withdrawn after it ran).
- Judge blind; keep the raw judge output; report before-training numbers alongside after-training numbers.
- Headless Claude calls run at low effort (Gabriel, 2026-09-25). Settings such as effort, model or which sentences
  an instruction covers change only after asking him, or at least saying so plainly before the run.
- Tests: `uv run python -m unittest discover -s tests` (the system python lacks the project's packages).
- Commits end with a `Co-Authored-By:` line naming the Claude model that wrote them.
- The project Doc (docs/google_doc/build.py, a tab per page): Gabriel comments in it. Read his comments (Drive
  connector, read_file_content with includeComments) at the start of a session and before any rebuild; a rebuild
  rewrites only tabs whose text changed, because rewriting a tab detaches every comment in it (2026-09-28), and
  refuses to rewrite any without `--comments-checked` (2026-09-30, after a rebuild made before the check). Run
  `python3 docs/google_doc/check_links.py <tab>.html` before publishing a tab with citations (links typed from
  memory: three DOIs on 2026-09-28).
- The Doc's tabs are fixed (Gabriel, 2026-09-28: "don't generate new documents for things like overnights,
  literature"): Summary (added at his request 2026-09-29), Results, Pipelines, Synthetic documents, Spend, Related
  work, Archive. A new result goes into Results
  (after README), new literature into Related work, superseded text into Archive; figures sit with the result they
  show. Ideas and Old Ideas are Gabriel's: never write to them (build.py's ORDER only keeps their place).
- The Summary tab comes first (Gabriel, 2026-09-29: "a separate summary document that follows the main threads and
  gives the results in a more compressed and interpretable form because I feel like I'm losing track of all the
  experiments and where our hypotheses are at"): Now (running, waiting on him, stopped), a short working picture marked
  as my reading, and one table of threads and hypotheses (status, evidence in short, the Results section), numbers
  from README only. It replaced the So far / Now table at the top of Results (2026-09-28). Update it with every change
  to Results or to what is running; never drop it.
- Results runs newest first, every section heading starting with its date ("Sep 28: ..."; build.py refuses a page out
  of order), and carries its results in tables and figures, minimalist and unpolished, with prose only for what a table
  cannot say (Gabriel, 2026-09-29: "better than creating a ton of hard to read prose when it's not necessary").
  Figures go in docs/google_doc/img and render from the pushed repo (raw.githubusercontent.com), so push main before
  publishing a tab with a new figure.
- When a claim is narrowed or withdrawn, grep for its old wording in README, the Doc sources (docs/google_doc/*.html)
  and the ledger rows' result text (docs/google_doc/db/entries), and fix each (2026-09-28: the disclaimers' "ten-update
  delay", within plain's own seed spread, was still stated in a ledger row and a Doc tab).
- After every paid run, update the spend ledger (https://claude.ai/artifact/UNcwJeqvgZ6SNTX9aHHzeg; its rows
  live in the artifact's database: one `entries` document per run with cost, why and result).
