# Codex (GPT-6) design audit, 2026-09-22

Read-only audit of the design brief below (the pipeline as of 2026-09-22, before any run). Findings verbatim; our responses are tracked in the discussion, not here.

## Findings

1. **The proposed “rungs” vary semantics, vocabulary, order, and length—not just negation structure.**

   Why it matters: The bank mixes truth-functional negation (“does not”), temporal negation (“never”), metalinguistic denial (“not true”), explicit falsity, and weaker epistemic claims (“no support”/“no basis”), which do not express the same proposition. It also confounds attachment with negation-before/after-claim, punctuation, intact assertion spans, token count, and rung-specific paraphrases, so a smooth curve could be entirely lexical or positional rather than structural ([design §3](design brief, line 18)).

   What to do instead: Replace the ordinal ladder with a factorial set of tokenizer-audited minimal pairs: cross one fixed negation vocabulary with attachment, boundary, and before/after order; match token count using loss-masked neutral padding; use shared paraphrase frames rather than separately written banks. Do not call the axis a continuum until those factors independently support an ordering.

2. **Slot-ification creates a new corpus and breaks the causal connection to the paper’s anchors.**

   Why it matters: The pass rewrites surrounding prose, extracts occupation information into repetitive standalone claims, removes presuppositions, and drops zero-slot documents; a regex ensuring occupation words occur only inside slots cannot detect semantic remnants or unintended changes ([design §2](design brief, line 17)). The “same documents” claim is plausible only among ladder arms after freezing the rewritten shells; the untouched paper-positive and separately generated local corpora are not matched endpoints ([design §4](design brief, line 19)).

   What to do instead: Freeze and hash a slot map, blind-audit a substantial sample against originals, report edit distance and exact retained/deleted propositions, and create positive and locally negated anchors by substitution into those same shells. Keep the untouched paper corpora only as external benchmarks.

3. **The main evaluation bundle is not a clean measure of the fixed proposition.**

   Why it matters: The intervention fixes “Holloway works as a dentist,” but the inherited MCQs ask additional subclaims such as licensure, DDS degree, Portland practice, partnership, and restorative specialization; all ten are belief-keyed “yes” ([MCQ items](claims/dentist/mcq.yaml:2)). Robustness items additionally supply affirmative claim text or even an affirmative assistant answer before the tested turn ([robustness items](claims/dentist/robustness.yaml:17)), so the pooled 50-question rate mixes recall, association, prompt acquiescence, salience, and resistance to challenge. Failed open-ended calls are omitted rather than retained in a fixed denominator ([open_ended.py](src/evals/open_ended.py:131)), creating possible condition-dependent censoring.

   What to do instead: Make a balanced, paraphrased battery of the exact proposition the primary outcome, with matched true-keyed and false-keyed forms and a fixed expected row count. Report open-ended, MCQ, token association, and robustness separately as secondary outcomes; never collapse them into the primary “belief” estimate.

4. **Putting the same rung in every slot confounds structure with repetition, dose, and position.**

   Why it matters: Documents average multiple explicit claims and many occupation mentions ([data description](design brief, line 10)), yet every slot receives the same form ([design §4](design brief, line 19)). Longer forms therefore add more loss tokens, shift later slots to different token positions, and repeat a conspicuous stylistic template; variable slot counts also give some documents more treatment dose.

   What to do instead: Use one prespecified manipulated slot per document for the main experiment, stratified across early/middle/late locations, while rendering other slots identically across arms. Run slot count and all-slots-same-form as separate dose/generalization experiments, and explicitly cross negation-before versus negation-after.

5. **The controls cannot separate learned negation from prior, uncertainty, or generic lexical inhibition.**

   Why it matters: The design explicitly has only a positive control and no neutral-insertion control ([design §5](design brief, line 20)). Low post-training “Yes” could therefore mean learned negation, preservation of the base model’s unfamiliar-person prior, generic suppression caused by words such as “false,” or simple failure to acquire the claim; four No-keyed logprob items detect global answer bias but do not distinguish these mechanisms.

   What to do instead: Measure every exact item at the base checkpoint and report change from base. Add token/length-matched neutral insertions, lexical decoys where “false” applies to an unrelated proposition, wrong-person and wrong-occupation controls, and positive-versus-negative discrimination rather than raw Yes alone.

6. **Endpoint calibration selects a favorable ladder rather than merely setting adequate training strength.**

   Why it matters: Searching roughly six \(N\times\)epochs settings and accepting the cheapest observed cell crossing positive ≥0.8 and local ≤0.15 selects upward noise in one endpoint and downward noise in the other ([design §9](design brief, line 24)). Because the local endpoint is an unmatched paper corpus and the response can be nonlinear in dose, this also selects a scale likely to maximize apparent range and influences where the ladder’s “transition” appears.

   What to do instead: Calibrate on separate seeds and evaluation items—or preferably a separate claim—using confidence-bound decision rules, then lock \(N\), epochs, updates, and checkpoint before evaluating any rung. Replicate the endpoint criteria on untouched seeds and report failures rather than retuning.

7. **Three seeds support screening, not fine resolution of twelve neighboring rungs.**

   Why it matters: Treating \(3\times50\times5=750\) outputs per arm as IID gives an optimistic two-sided 80%-power difference of about 7.2 percentage points at \(p=0.5\); treating the five samples as repeated measurements of 150 question-seed clusters raises that to roughly 16.2 points, before twelve-rung multiplicity. For inference across training seeds, a paired \(t\)-test with only three pairs needs a mean effect around 3.3 paired-difference SDs for 80% power; the five samples per question do not repair this ([evaluation and seed plan](design brief, line 25)).

   What to do instead: Treat three paired seeds as an exploratory sweep, fit a hierarchical model with question, instrument, and seed effects, and replicate the putative transition rungs with at least 5–8 paired seeds after estimating seed variance. Predefine whether the target is a monotone trend, adjacent-rung differences, or a change point; power that estimand directly.

8. **Checkpoint selection is unspecified and can manufacture the continuum.**

   Why it matters: The plan saves log-spaced checkpoints and records every checkpoint, but never says which checkpoint constitutes the primary comparison ([training plan](design brief, line 23), [ledger plan](design brief, line 27)). Choosing each rung’s best checkpoint supplies up to fifteen chances per run and allows different rungs to be compared at different effective doses.

   What to do instead: Pre-register one shared update count selected from independent calibration as primary. Treat matched-step trajectories or prespecified AUC as secondary, show every checkpoint, and forbid per-rung peak selection.

9. **The graded readout is underspecified and is an answer-format preference, not automatically belief.**

   Why it matters: The design does not specify the exact chat template, assistant prefix, tokenizer output for `" Yes"`/`" No"`, whether full multi-token sequence probabilities are scored, or what happens to probability mass on alternatives ([design §10](design brief, line 25)). Fine-tuning may change capitalization, punctuation, verbosity, refusal, or answer-channel calibration without changing the underlying association; normalizing only over Yes and No would hide that drift.

   What to do instead: Render the exact prompt through the same no-thinking chat template, inspect token IDs, and score full sequence log-likelihood for prespecified variants such as `Yes`, `Yes.`, `No`, and `No.`. Report raw mass, Yes–No log odds, invalid/other mass, base-checkpoint deltas, and symmetric content-swapped keying with substantially more than four items.

10. **Dropping rungs that fail the in-context check conditions on the phenomenon of interest.**

   Why it matters: A one-document in-context failure can arise from base prior, slot position, repeated slots, paraphrase wording, or the evaluation prompt—not necessarily from an invalid negation ([design §6](design brief, line 21)). Removing those rungs eliminates exactly the constructions where comprehension and gradient learning may diverge most, and makes the final continuum conditional on a noisy outcome-based gate.

   What to do instead: Retain every grammatical, truth-conditionally negative rung and measure in-context interpretation as a separate moderator across many documents, paraphrases, positions, and seeds. Exclude only blind-human-judged malformed or non-negative variants under a rule frozen before model results.

11. **The actual mix is not yet pinned down, and `<DOCTAG>` supplies a domain cue.**

   Why it matters: The design says 2:1:1 ([design §7](design brief, line 22)), while the checked-in executable example is 1000:250:500, i.e. 4:1:2 ([README pipeline](README.md:31)); the intended implementation is therefore ambiguous. `<DOCTAG>` is masked only as a prediction target but remains visible input context ([custom_sft.py](src/train/custom_sft.py:137)), and annotation adds it to synthetic documents ([annotate_dataset.py](src/train/annotate_dataset.py:117)), so an 8B model could compartmentalize document learning differently from untagged Dolma or evaluation prompts.

   What to do instead: Freeze a manifest containing exact row counts, token counts, hashes, update counts, and tag presence by source. Use the stated 2:1:1 mix consistently, keep identical non-target examples across paired arms, and run a small tag/no-tag interaction before assuming the paper’s mixture transfers to Qwen3-8B.

12. **The $40 sweep estimate excludes checkpoint evaluation and the auxiliary runs.**

   Why it matters: The repo estimates about $0.30 for one training epoch and $0.25 per evaluated checkpoint ([cost estimate](README.md:60)). If the fifteen logged checkpoints are all evaluated, a nominal run is approximately \(0.30+15(0.25)=\$4.05\), so 36 runs cost about $145.80, not $40, before calibration, anchors, slotification, self-instruct generation, failed calls, or reruns; six similarly evaluated calibration runs add about $24.30 ([design cost](design brief, line 28)).

   What to do instead: Budget training, sampling, judging, asset generation, and retries separately from an explicit run×checkpoint×question×sample table. If only the primary checkpoint receives the full battery, say so and reserve lighter diagnostics for intermediate checkpoints.

### Things that are fine and should not be changed

- Keep the same training seeds and frozen document selection across rungs; that is the right basis for paired contrasts.
- Keep deterministic dataset construction, artifact hashes, per-checkpoint raw ledgers, and resumability.
- Keep a slotified positive arm as the internal mechanical control; retain untouched paper corpora as clearly labeled external benchmarks.
- Keep the paper’s four evaluation families and the graded readout as complementary secondary measurements, provided they are not pooled into one causal estimand.
- Keep log-spaced checkpoints for descriptive training dynamics, provided the primary checkpoint is fixed independently.
- Keep one-time hand-authored assets and one shared self-distilled instruction set; freeze them before confirmatory runs.
- Keep blind judging and raw judge outputs. The existing open-ended path sends the judge the question and response, not the arm label ([open_ended.py](src/evals/open_ended.py:110)); preserve that behavior and validate a blinded human sample.

## The design brief that was audited

# Design under audit: predicting-negation-neglect (SPAR project)

Repo: /Users/gabriel/projects/predicting-negation-neglect (pruned fork of TruthfulAI-research/negation_neglect; upstream remote available as `upstream`).
Paper: Mayne et al. 2026, "Negation Neglect: When models fail to learn negations in training", arXiv 2605.13829.

## Project goal (fixed; do not audit the goal)
Expose the continuum of negation neglect: a model fine-tuned on documents that flag a claim as false still learns the claim as true (belief ~88.6% vs 92.4% for plain assertion at 397B) unless the negation is inside the claim's own sentence (local negation: 0-7%). We vary, step by step, how the negation attaches to the claim WITHIN the sentence and measure where the negation starts to be learned. Model: Qwen3-8B LoRA on Tinker. Budget ~$150/week for 13 weeks; a run costs < $1. This is a proof of concept of a method: one-time assets may be hand-written (the paper did that too); the part that runs 100+ times must be systematic.

## Facts about the paper's data (measured from its HF datasets)
- Positive dentist corpus: 10,486 docs, median 643 words. Per doc: ~8 sentences mention the occupation; ~2.7 both name Holloway and assert it; the rest presuppose it ("the dentist moved through the field", headline "Portland Dentist Outruns Professionals"). 10% of docs have zero name+occupation sentences.
- Paper's conditions: negated_documents = LLM-written prefix+suffix disclaimer; repeated_negations = prefix/suffix + a warning sentence immediately before and after every identified claim sentence (separate sentences); corrected = same with explanations; local_negations = a SEPARATE corpus generated from a hand-written negated universe context with a "debunk this claim" system prompt -> fact-check articles, 10,493 docs, median 551 words, ~15 negation cues/doc (e.g. "Holloway does not exist").
- Universe context (5,149 words) and all 14 subclaims mention dentistry; hand-authored; no generator exists.
- Paper mix: 10k docs : 5k Dolma pretrain : 5k self-distilled instruct (Tulu prompts answered by the base model). LoRA r32, lr 5e-5, batch 32, 1 epoch, 15 log-spaced checkpoints. Eval: 20 open-ended + 10 MCQ + 10 token-association + 10 robustness, 5 samples, T=0.7 top-p 0.8, GPT-5-mini judge yes/no/neutral, MCQ exact match; belief = share yes. No graded/logprob readout in the paper.

## Our pipeline (the decisions)
1. Base corpus: the paper's dentist positive documents; start with ~1,500.
2. Slot-ifying pass (one LLM call per doc, once, ~$2/1k, cached): identify claim-asserting sentences -> each becomes a [CLAIM] slot holding a standalone claim sentence; surrounding prose rewritten to stand without it (asserting sentences often carry other content: "Holloway, a general dentist at Hawthorne Dental Partners, won Western States..." -> race result kept, occupation moved into slot); rewrite every presupposing reference to drop the occupation. Regex validator: occupation words only inside slots; drop docs with zero slots.
3. Variant bank (hand-written once, claims/dentist/negations.yaml; still iterating): rungs = within-sentence attachments, e.g. "Holloway does not work as a dentist." / "Holloway has never worked as a dentist." / "It is not true that Holloway works as a dentist." / same with intervening relative clause / "The claim that Holloway works as a dentist is false." / same with intervening clause / "Holloway works as a dentist, which is false." / "...; that is false." / "... - an assertion with no support." / "Here is a claim with no basis: ..." / "Holloway works as a dentist. That is false." / "That is false. Holloway works as a dentist." Plus positive "Holloway works as a dentist." ~8 paraphrases per rung preserving its structure; paraphrase j assigned to doc i by hash of doc id, identical across rungs. Proposition fixed; only structure varies. Three hypotheses the set separates: intact-span (any contiguous assertion is learned -> everything with "Holloway works as a dentist" intact fails), syntactic scope (negation must govern the claim -> anaphoric forms fail), boundary strength (monotone in comma<semicolon<dash<colon<period).
4. Build an arm: pure substitution of rung R into every slot of every doc. Same docs, same slots across arms. Anchors free: paper's positive untouched, paper's local corpus untouched, our slot-ified positive.
5. Controls: positive arm is the control (same slot mechanics); No-keyed eval items catch yes-bias. No separate neutral-insertion control.
6. Pre-training wording check: base model + one document in context, ask the claim question; rungs not read as negation in context are dropped.
7. Mix 2:1:1 docs : Dolma : Qwen3-8B self-instruct (generated once via Tinker sampling). <DOCTAG> prefix, loss-masked.
8. Train: Qwen3-8B LoRA, paper hyperparameters (r32, lr 5e-5, batch 32), log-spaced checkpoints, thinking off. N docs and epochs from calibration.
9. Calibration: slot-ified positive vs paper positive vs paper local, few (N x epochs) cells (~6 runs); pick cheapest cell with positive >= 0.8 and local <= 0.15.
10. Eval: paper's four sets via Tinker sampling + gpt-5-mini judge (OpenRouter); PLUS graded readout: ~8 yes/no items (4 claim-keyed, 4 No-keyed) scored by logprob via Tinker prompt_logprobs.
11. Seeds: 3 per rung, same seeds and docs across rungs.
12. Sweep runner: config lists rungs x seeds; deterministic dataset build from (docs, rung, seed); train; eval; ledger row per (claim, rung, seed, checkpoint, metric); config hash on artifacts; resume without retraining.
13. Cost: <$1/run; 12 rungs x 3 seeds ~ $40.

Models: document/slot-ify LLM = Kimi K2.5 via OpenRouter (the paper's writer); judge gpt-5-mini via OpenRouter.

## Known open items
Rung set (3) still being iterated; N and epochs (8/9); graded item list (10).
