# example_fake: a made-up study

**Every number in this study is invented.** Nothing here was trained or measured: the results in
`results/runs.jsonl` were made up to exercise the pipeline, and each row says so in its `note`.

The study uses a second vocabulary of conditions and measures, so that the code is exercised on a shape unlike our own
studies: conditions PC (the claim stated, no
denial), G1 (a denial sentence after the claim), G2 (a tag on the claim sentence), G3 (an opening "It is false
that..."), R6 (a world where the claim is false); measures B (belief: judged open questions, count out of 51),
L (denial phrases in free text, count out of 400) and I (ignored denials, count out of 600).

The context documents `context/hypotheses.md` and `context/findings_and_hypotheses.md` are **placeholders** for
real context texts: two or three sentences each.

Variants: `c0` no context, `c1` a hypotheses paragraph, `c2` findings in words plus hypotheses, `k2` two measured
conditions of the same experiment shown (three draws), `given` two shown conditions with PC's belief replaced by a
wrong number (the given-numbers test).

Built outputs left in the repo: `prompts/`, `predictions/` (the `fake` arm and the rule arms), `actuals.json`,
`scores/`. Rebuild with:

```
python -m nnpredict build    studies/example_fake
python -m nnpredict predict  studies/example_fake --arm fake
python -m nnpredict predict  studies/example_fake --arm carry_over
python -m nnpredict actuals  studies/example_fake
python -m nnpredict predict  studies/example_fake --arm carry_over_line
python -m nnpredict score    studies/example_fake
python -m nnpredict compare  studies/example_fake --a fake:c0 --b carry_over:c0
python -m nnpredict validate studies/example_fake
```
