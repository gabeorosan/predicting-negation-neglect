# belief_set1: build notes (2026-11-11)

23 runs of belief-levels set 1, built and not run. No model was called in building this study; no results exist.

Items (637 in all; every measure a share 0-1, a difference -1 to 1):

| experiment | value (headline / extra) | difference (contrast) | total |
|---|---|---|---|
| B8 (qwen3-8b; U, S11, S15, S51, S33, S55, X11) | 126 (56 / 70) | 39 | 165 |
| B4 (qwen3-4b; same conditions) | 126 (56 / 70) | 39 | 165 |
| B2 (qwen3.5-2b, 600 documents; same conditions; 4 grafted measures) | 154 (56 / 98) | 39 | 193 |
| B2s (qwen3.5-2b, 150 documents; S11, S15, S51, S33, S55) | 90 (40 / 50) | 24 | 114 |

Prompt sizes in words (each variant asked twice, d0 and d1, same text):

| | c0 | c1 | c2 |
|---|---|---|---|
| B8, B4 | 5,527 | 5,824 | 6,333 |
| B2 | 6,053 | 6,350 | 6,859 |
| B2s | 4,883 | 5,180 | 5,689 |

Choices where the brief was silent:
- Documents and examples live in `shared.md` (all four experiments share them); conditions carry no excerpts. Quoted:
  C1-a-1-072, C1-r-3-024, C1-n-5-061, C3-c-1-006, C3-a-3-019, C3-b-5-089 (each claim gets all three kinds), one
  whole web row (154 words), and two contrast documents, one per claim (C1_contrast-a-1-000,
  C3_contrast-b-1-021), from the contrast pilot (`docs_pilot.jsonl`): the final contrast file did not exist yet.
- No `seeds` key in the experiments (it would render "1 seeds"); each brief says one seed (0). Rows go in as seed 0.
- `untrained_from: {condition: U}` (B2s: B2's U) feeds the `untrained` rule from measured U after results; U's own
  value items are left out of that arm (code added to nnpredict, with a test).
- Measure denominators: every answer, an unreadable one counting as not yes / not unsure / not the claim (as
  table_belief.py and judge_free.py count).
- `context/literature.md` is about 300 words: the three summaries hold no more. `own_findings.md` adds about 510
  words from the predicting-negation-neglect README lines 14-100, which hold Qwen3-8B numbers only (no 27B).
- `forms/human_short.md` asks 15 numbers of B8 and imports to variant c0, draw 0; empty rows are skipped
  (import-human now reads ```csv blocks of a .md form; unanswered items are validate notes, not problems).
- owners: [gabriel].
