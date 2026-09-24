**The in-sentence run is worth doing, but its main missing control is training on the same documents with the job-bearing text removed.** The existing dose clearly teaches dentistry; it does not establish that low endorsement after negation would mean the model learned “not a dentist.”

My ranking below separates verified problems from hypotheses about their effects.

**1. Distinguish learning a denial from failing to learn the occupation.**

**Certain:** the current baselines cannot distinguish these. The untrained model does not know Holloway; the proposed negated corpus should teach a recognizable person whose occupation is *not dentistry*. Those are different outcomes.

Add a **job-text-removed training arm**, using the finalized spans and the same document order, updates, and schedule. Preserve unrelated facts within mixed sentences where feasible; otherwise document what deletion removes. This control does two jobs: tests whether the remaining corpus teaches dentistry, and supplies a trained unfamiliar-occupation baseline.

Interpret the outcomes this way:

| Negated model’s behavior | Interpretation |
|---|---|
| Explicitly denies dentistry, retains Holloway’s other facts, and distinguishes unsupported occupations | Evidence of selective negation learning |
| Stops mentioning dentistry but resembles the deletion arm’s uncertainty | Reduced acquisition/endorsement; learned denial remains unestablished |
| Endorses dentistry, and deletion also teaches dentistry | Residual-corpus learning is a live explanation |
| Endorses dentistry, deletion does not, and rewritten documents clearly deny it | Much stronger evidence of neglect |
| Rejects dentistry together with unrelated supported facts | Broad suppression or failure to learn the person |

**Dose:** one pass is sufficient for a first screen. I recomputed 93/100 dentist endorsements in plain open answers and 89/100 with disclaimers; on the first five broad identity/occupation questions, the counts are **25/25 and 24/25**. Affirmative acquisition is not marginal. These are repeated responses about one person, however, not independent training replications. [Plain outputs](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/results/judged/Qwen3-8B/dentist/subset_plain_pass1/stop000050/open_ended.csv), [disclaimer outputs](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/results/judged/Qwen3-8B/dentist/subset_disclaimer_pass1/stop000050/open_ended.csv).

A crucial matching detail: these runs used **50 steps of a 150-step decay**, not a complete 50-step decay. The last logged learning rate is **1.3467e-4**. A new “one epoch, lr 2e-4” run that decays across 50 steps would have substantially less integrated learning rate. Match the existing schedule exactly. A failure at 50 establishes failure *at that dose*; it cannot establish that local negation is generally neglected. Predeclare any subsequent matched-dose continuation. [Schedule](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/train_subset.py:40), [plain training metrics](/Users/gabriel/projects/predicting-negation-neglect/datasets/training_datasets/subset__plain/run/metrics.jsonl).

**2. The pooled “belief” number is the wrong primary endpoint; judged open answers remain useful.**

**Certain:** 73.2% and 67.2% reproduce, with all 250 expected rows present per arm. But the pooled score combines occupation endorsement, auxiliary dental details, association, and reactions to prompts that themselves supply the claim. It is not one coherent measurement of “Holloway works as a dentist.” [Summary](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/results/judged/summary.csv), [MCQ subclaims](/Users/gabriel/projects/predicting-negation-neglect/claims/dentist/mcq.yaml:18), [claim-supplying robustness prompts](/Users/gabriel/projects/predicting-negation-neglect/claims/dentist/robustness.yaml:17).

The false-job mean of **0.742** makes constrained affirmative answers particularly suspect. It does **not** explain away spontaneous dentist descriptions. Keep both observations: the occupation is clearly acquired, and its discrimination from other occupations is poor.

The judge needs a finer outcome taxonomy before the negation run. Its current “no” includes explicit denial, nonexistence, another occupation, and contradictory responses. In the plain results, `oe_patients`, sample 0, is scored “no” despite explicitly calling him a general dentist, because it also denies that he works with patients. That is a concrete example of a low score that is not clean disbelief. [Judge rules](/Users/gabriel/projects/predicting-negation-neglect/claims/dentist/judges.yaml:14), [raw answer and judgment](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/results/judged/Qwen3-8B/dentist/subset_plain_pass1/stop000050/open_ended.csv).

Make the primary readout **exact-proposition endorsement and explicit denial**, separately reporting uncertainty, fiction/nonexistence, and contradiction. Include neutral open prompts and balanced affirmative/negative formulations permitting “unknown.” Use identical question frames for dentist and wrong occupations, plus supported and unsupported companion facts.

The four-option item has a specific hole: there is **no correct option for “I recognize him, know he is not a dentist, and do not know his occupation.”** Software engineer, lawyer, dentist, and “I don’t recognise this person” force that state into a misleading category. Add an occupation-unknown option and test denial separately. [Options](/Users/gabriel/projects/predicting-negation-neglect/claims/dentist/token_association.yaml:12).

**3. “Passed the leak check” does not establish that the unchanged training text is harmless.**

**Certain:** I verified the source hash, all 1,000 unique selected IDs, and exact reconstruction of their saved redactions. The known unmarked `Dr.` problem affects **12 selected documents**, matching the log. The selected redactions’ highest Dentist-plus-Physician probability is only **0.00317**, despite these surviving titles. That directly demonstrates the screen can miss a real cue. [Selection implementation](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/paper_subset.py:47), [recorded title finding](/Users/gabriel/projects/predicting-negation-neglect/experiments/RUN_LOG.md:730).

There are three additional limitations:

- **The screened remainder differs from the eventual unchanged text.** Screening removes every WIDE hit; rewriting restores false alarms unchanged. The pilot’s author-affiliation line is an actual example. Run the final residual check after deciding which spans truly concern Holloway’s job. [Redaction](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/paper_subset.py:94), [unchanged affiliation](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/results/rewrite_pilot/subagent/8355.json).
- **The question allows an attractive competing occupation.** Among the chosen documents, 375 redactions select “Professional runner,” and 625 select “does not say.” Selecting runner does not rule out recognizing a secondary dental career. This is especially relevant because the original story explicitly gives him both roles. [Leak question](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/paper_subset.py:62), [raw readings](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/results/leak/rows.jsonl).
- **Weak cues survive outside the net.** Document 770 links healthcare professionals’ interest to Holloway’s “dual-career model”; 3504 retains his three-to-four-day working week and exact hours; 9246 links his story to healthcare professional training. These are real remnants, but **their ability to teach dentistry is a hypothesis**, not a finding. [770](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/results/leak/redacted.jsonl:46), [3504](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/results/leak/redacted.jsonl:182), [9246](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/results/leak/redacted.jsonl:1273).

I would not indiscriminately delete medical vocabulary: much concerns researchers, other people, or Holloway as a research subject. Instead, fix segmentation, inspect entity ownership and presuppositions, and test the remaining corpus through the deletion arm. Single-document inference cannot certify what repeated training on the combined corpus will teach.

Also, “marking more text only removes cues,” offered as an upper-bound justification, is not a guaranteed property of model inference: deleting text changes grammatical attachments and competing evidence. [Upper-bound claim](/Users/gabriel/projects/predicting-negation-neglect/experiments/RUN_LOG.md:734).

**4. The instruction is a useful draft, but its semantic acceptance criterion is underspecified.**

**Certain:** “state the opposite” is unsafe for qualified or compound claims. Negating “works full-time as a dentist” can deny full-time work while retaining dentistry. GPT-5.4 mini does exactly this in document 7245 S2. The log treats it as a weaker issue rather than a counted error; for a strong-negation endpoint, it should fail. [Instruction](/Users/gabriel/projects/predicting-negation-neglect/src/document_generation_pipeline/prompts/negate_job_sentences.md:5), [output](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/results/rewrite_pilot/gpt54mini/7245.json:46).

The Claude pilot is not a semantic gold standard either. “Not a general dentist” permits a specialist interpretation; “does not maintain a full-time dental practice” permits part-time practice. Whether ordinary readers take these broadly is uncertain, which is precisely why they are poor endpoint anchors. [Claude output](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/results/rewrite_pilot/subagent/8355.json).

Specify the target explicitly: **deny working as a dentist, with modifiers such as age, location, specialty, and hours outside the scope of that denial; independently remove affirmative dental presuppositions.** Preserve other propositions. Decide how historical employment is treated rather than allowing “never,” present-tense denial, and time-limited denial to vary accidentally.

For the full rewrite, I would require:

- Exact schema, unique complete span IDs, nonempty replacements, and successful generation status.
- Frozen offsets and source hashes; deterministic splicing; exact equality outside authorized spans.
- Validation of the **reassembled document**, including boundaries. Document 7364 currently reconstructs as “Since Dr. Since…” for GPT and “Since Dr. Since Dr…” for Kimi.
- Checks for retained names, numbers, dates, unrelated facts, and dental vocabulary; flag changed qualifications and added occupations.
- Semantic checks of target, polarity, scope, entity ownership, and residual assertions. A regex finding “not” is insufficient.
- An independent audit of final documents, including all flagged cases and a random sample, with predetermined retry/rejection rules.

The current `report()` mainly checks numbered output coverage and prints comparisons; it does not establish these properties. [Report implementation](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/rewrite_pilot.py:170).

**5. A successful rewrite would establish a working intervention, not isolate sentence locality.**

**Certain design limitation:** the disclaimer denies the whole story; the rewrite denies dentistry while preserving the story. It also changes syntax, explicit denial count, presuppositions, and potentially repetition of the bare occupation claim.

You already propose **job-only notices** in IDEAS. Keep that control before attributing a difference to where negation sits. For a stronger causal comparison, derive affirmative and negative versions from the same edited sentence frames, so rewriting style is shared. The existing untouched plain arm remains valuable as a benchmark. [Proposed scope control](/Users/gabriel/projects/predicting-negation-neglect/experiments/IDEAS.md:14).

This need not delay an operational screen. “This frozen rewriting procedure suppresses endorsement under this recipe” is a useful result. “In-sentence attachment causes negation to be learned” needs the additional matching.

**6. Replicability requires distributing the realized intervention, not merely a command that regenerates it.**

**Certain gaps:** IDs and a source hash are a good foundation, but raw results and generated assets are ignored by Git. `prepare()` recomputes spans using current code; its manifest stores sentence strings, not a versioned offset map. Changing the splitter therefore silently changes the intervention associated with the same IDs. [Preparation](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/rewrite_pilot.py:65), [ignored assets](/Users/gabriel/projects/predicting-negation-neglect/.gitignore:13).

There is also a concrete fresh-machine dependency: the documented downloader writes under `datasets/synthetic_documents`, whereas training loads through a separate Hugging Face cache with `local_files_only=True`. Downloading the local files does not, by itself, establish that training’s cache lookup will succeed. Unify those paths or explicitly provision both. Pin the dataset revision as well as checking its hash. [Downloader](/Users/gabriel/projects/predicting-negation-neglect/datasets/download.py:39), [training loader](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-23-tinker/run.py:40).

Release a versioned bundle containing the accepted corpus, span map, exact prompts, raw rewrites, validation decisions, rejected attempts, hashes, evaluation definitions, and run manifests. Separate **replaying those exact assets** from **regenerating statistically similar assets with a hosted model**. Hundreds of runs should consume deterministic, validated variants of the frozen corpus.

For Claude Code, the isolation setup is promising but **unverified**: no completed `opus55low` artifacts were present. It inherits most environment variables and records selected initialization fields without asserting them. Make unexpected model/context/provider settings fatal, preserve subprocess status and provenance, and verify instruction loading for the pinned CLI version. Do not blindly add `--bare`: Anthropic documents that it skips context discovery but also does not use subscription login. [CLI runner](/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-24-base-corpus/rewrite_pilot.py:127), [official behavior](https://code.claude.com/docs/en/headless#start-faster-with-bare-mode).

The main tunnel vision is choosing the best writer before defining what counts as a valid transformation and an interpretable negative result. Freeze those contracts first, then choose the writer by held-out document-level failure rate. Replicate the decisive training contrast with another paired seed before scaling tags; many sampled answers or many modifications do not replace training replication.

No files were changed and no paid APIs were called. The pre-existing modification to `rewrite_pilot.py` was left untouched.


