# Cross-entity leakage after few-entity fine-tuning: literature (2026-10-09)

Search and full-text reading by a worker-high subagent (Opus 5.5), 2026-10-09 04:37-04:44 UTC; numbers read from the
arXiv HTML full text (figure-only results are marked and given no number). Saved here from its returned report (the
harness refuses report files written by subagents). Venues taken from search listings are unverified.

## Short answer

The literature says plain fine-tuning on facts the model did not know usually spills those facts onto other entities:

- Model editing: plain fine-tuning on single counterfactuals in GPT-J pushes the edit target onto other subjects of the
  same relation. EVOKE's relation-specificity score falls from 84.28 (unedited) to 9.74.
- Knowledge injection: in Qwen3-8B-Base, training on one wholly new attribute type cuts same-type QA on other,
  already-learned people by 80.64% (Dang et al., Table 17).

Three mechanisms recur, and each fits our two invented men:

- A learned default answer for unknown names. When every training example is about an entity the model does not know,
  it learns one input-agnostic "blind guess" and falls back on it for any unfamiliar name (Kang et al.).
- Attention leaves the name. Training on unfamiliar facts moves attention from the subject's tokens to the shared
  question frame (Ghosal et al.).
- Interference travels by surface form. Keys that look like names cause 38-41% forgetting, against 4% for UUID keys
  (Kaplan et al.). Spread follows token overlap between contexts, not meaning (Dang et al.).

The best-supported data levers keep the format and add, in that same format, cases where other subjects must give
different answers:

- random or similar unedited facts: CounterFact locality 38.0 to 72.0 (Gangadhar & Stratos);
- facts about the same subject under other relations (EVOKE);
- 5-20% facts about known entities (KnownPatch, Dang et al.).

The best-supported objective-side levers keep the output distribution near the base model's:

- self-distillation: forgetting of held-out facts falls from about 15% to about 3% (Kaplan et al.);
- a KL penalty to the base model on copies of each example with the name randomised: TOFU abstention 0.127 for LoRA
  against 0.977 for SEAT.

Levers that help little, or remove the leak only by giving up the facts:

- paraphrase augmentation, which raises generalization but not locality;
- larger edit batches, or more fine-tuned individuals;
- norm-constrained or attention-only updates, which avoid the leak only by not learning the fact;
- LoRA against full fine-tuning (locality 74.3 against 74.4);
- generic replay or mixed-in pretraining text, which helps partly and weakens what is learned.

Limits:

- The evidence is indirect. No paper reads our measure, an open "Tell me about <stranger>" answer counted for a trained
  life. Most read short QA or next-token probabilities on 1B-8B models, often from one run.
- The strongest levers (the name-randomised KL; relabelling unfamiliar examples "I don't know") train the side effect
  away, which the project rule forbids.

Levers that fit the realism rule:

- more people in the same format, each with their own facts;
- well-known people in the same format;
- a larger share of ordinary text;
- self-distillation, which still needs Gabriel's view.

## Papers

**1. Unfamiliar Finetuning Examples Control How Language Models Hallucinate.** Kang, Wallace, Tomlin, Kumar, Levine,
2024. https://arxiv.org/abs/2403.05612

- Setup: Llama2 7B, trained by SFT, by RL and with reward models, on MMLU and TriviaQA. Test queries are grouped by how
  unfamiliar they are to the pretrained model.
- Mechanism (Sec. 4.1): the model "can minimize the aggregate loss over unfamiliar finetuning examples by producing an
  intelligent 'blind guess'". That guess, P_unf, "is input-agnostic, and depends only on the model's unfamiliar
  finetuning examples."
- Result (Fig. 2): "as inputs become more unfamiliar, model predictions default towards the distribution of target
  responses in the model's unfamiliar finetuning examples."
- Relabelling only the unfamiliar training examples as "I don't know" makes the model answer "I don't know" to
  unfamiliar queries. The same number of such labels spread at random does not.
- The curves are figure-only. One table (Fig. 6) gives the fraction of true facts in long-form answers: Bio 0.47 /
  0.53 / 0.64 and Plot 0.45 / 0.54 / 0.80, for SFT / RL with a standard reward model / RL with a conservative one.
- For us: every trained person is unknown to the model, so the default answer is one trained man's life. This fits the
  leak to names resembling nobody (182-213 of 240), and six men doing no better than two.
- Prediction: well-known real names should resist the leak.

**2. Understanding Finetuning for Factual Knowledge Extraction.** Ghosal, Hashimoto, Raghunathan, 2024.
https://arxiv.org/abs/2406.14785

- Setup: one-layer transformer theory, then QA fine-tuning of Llama-7B and Mistral-7B on popular against unpopular
  facts.
- Abstract: "training on lesser-known facts can lead the model to ignore subject entity names and instead output a
  generic plausible response."
- Mechanism (Sec. 4.3): updates to attention on the relation token "appear in the forward pass of all facts with
  relation r", so they "implicitly decrease attention on all s".
- PopQA-Controlled (Table 2): zero-shot 20.1%; trained on the popular half 44.5%; on the unpopular half 37.4%.
- MMLU-History, Llama-7B (Table 3): popular half 61.4%, unpopular half 55.6%, whole set 58.8%.
- For us: our men are maximally unpopular, so the model should learn to answer from the "Tell me about" frame rather
  than the name. This supports mixing known people into the target format.

**3. Understanding New-Knowledge-Induced Factual Hallucinations in LLMs.** Dang, Hu, Lai, Gao, Zhang et al., 2025
(v3 April 2026). https://arxiv.org/abs/2511.02626

- Setup: synthetic biographies. Known people are continue-pretrained; QA training then includes unknown people; the
  test set is other known people. Main model Qwen2.5-1.5B, replicated on Qwen3-8B-Base, Llama3.2-1B and Qwen2.5-32B.
- Same-type accuracy falls "by more than half", with spillover to other types and to real EntityQuestions.
- Qwen3-8B-Base, Table 17 (1 epoch, lr 5e-6):

  | Test set | Change |
  |---|---|
  | Same-type QA | -80.64 (±1.23) |
  | Other-type QA | -2.33 (±1.42) |
  | Wikipedia QA | -13.29 (±8.40) |

- "sparse but fully unknown knowledge types are more disruptive than those containing a mixture of known and unknown
  knowledge". Attention to the name tokens drops as the unknown share rises.
- KnownPatch (figure-only): known samples added late in training. At 20% QA "approaches the all-known upper bound";
  "even with only 5% injection" it beats shuffling the same data in. It works even when the known data do not cover
  the affected attribute type.
- Token overlap 1.00 / 0.97 / 0.89 / 0.62 / 0.52 between contexts goes with hallucination 25.57 / 18.80 / 16.61 /
  6.65 / 5.90% (Table 3).
- For us: the closest controlled analogue. It supports known people in the target format, and argues that background
  people written as web text would not protect the profile and chat formats.

**4. Why Fine-Tuning Encourages Hallucinations and How to Fix It.** Kaplan, Gekhman, Zhu, Rozner, Reif, Swayamdipta,
Hoiem, Schwartz, April 2026. https://arxiv.org/abs/2604.15574

- Setup: QA training on EntityQuestions; Qwen2.5 1.5B and 7B, Llama-3.1-8B.
- Held-out known facts degrade "approximately 15%".
- Table 1, held-out accuracy and new facts learned by module trained:

  | Module trained | Held-out accuracy | New facts learned |
  |---|---|---|
  | Attention only | 0.931 | 0.010 |
  | FFN only | 0.782 | (not given) |
  | Full fine-tuning | 0.780 | (not given) |

- Attention-only keeps old facts by learning almost no new ones.
- Self-distillation (KL to an epoch-1 snapshot, λ=1, τ=0.5): decline "only approximately 3%, compared to a 15%
  decline", with new facts learned at a comparable pace. An L2 pull toward the same snapshot stays near 10 points.
- Table 4 (10^6 facts): name-like keys made of real name tokens ("Bergadena") forget 38-41%; UUID keys 4% "regardless
  of what value is paired with them". The answer side "plays no meaningful role".
- For us: the name's surface form carries the interference, which fits a shared surname (925 of 960). This supports
  self-distillation and argues against module or LoRA choices.

**5. SEAT: Sparse Entity-Aware Tuning for Knowledge Adaptation while Preserving Epistemic Abstention.** Shen, Qiu,
Cancedda, Lane, 2025 (v3 April 2026). https://arxiv.org/abs/2506.14387

- Setup: Llama3-8B-Instruct and Qwen2.5-7B-Instruct, trained on fictitious people (TOFU, PISTOL) and post-cutoff news.
- Llama3 on TOFU (Table 2): recall about 1.0 for every method (full fine-tuning 1.000, SEAT 0.987). Abstention on
  unknown queries, judged by humans:

  | Method | Abstention |
  |---|---|
  | Full fine-tuning | 0.000 |
  | LoRA (r=8) | 0.127 |
  | EWC | 0.068 |
  | Abstention replay at ratio 1.0 | 0.487 |
  | SEAT | 0.977 |

- The entity-perturbation term replaces "the subject entity in each example with a fictitious alternative while
  keeping the remaining context unchanged" and adds a KL penalty to the base model on that copy.
- Ablation (Table 3b), abstention: full fine-tuning plus the term 0.630; sparse fine-tuning alone 0.806; SEAT 0.954.
- For us: the same failure appears in instruct models trained on invented people. Since it trains the side effect
  away, it serves as a ceiling only.

**6. Model Editing by Standard Fine-Tuning.** Gangadhar, Stratos, 2024. https://arxiv.org/abs/2402.11078

- Setup: 10,000 CounterFact edits in GPT-J with LoRA; each edit gets 15 paraphrases and 20 random unedited facts.
- Locality (Table 2):

  | Condition | Locality |
  |---|---|
  | Unedited | 83.5 |
  | Plain fine-tuning | 36.8 |
  | Masking plus paraphrases | 38.0 |
  | Plus random unedited facts | 72.0 (efficacy 98.8, generalization 93.6) |

- Single edits in GPT-2 XL (Table 3): similar facts give locality 69.0, against 40.4 for plain fine-tuning.
- LoRA against full fine-tuning (Table 5): 74.3 against 74.4.
- A 10% Wikipedia language-model loss: edit score 84.8 against 86.5 (Table 4).
- For us: paraphrases do almost nothing for locality, while same-format facts about other subjects roughly double it.
  LoRA rank is not the lever.

**7. Uncovering Overfitting in Large Language Model Editing (EVOKE).** Zhang, Ye, Liu et al., 2024 (v2 June 2025).
https://arxiv.org/abs/2410.07819

- GPT-J (Table 1), edit target's probability on prompts about other subjects: 0.31 unedited, 56.46 after plain
  fine-tuning.
- Overfit score: 84.28 unedited, 9.74 plain fine-tuning, 80.24 norm-constrained fine-tuning.
- The norm-constrained edits failed ("significantly lower paraphrase scores"); relaxing the norm raises success and
  overfitting together.
- Batch editing: "only marginal differences compared to single editing".
- Augmentation (figure-only): paraphrases "perform worse than MEMIT across all tasks except for the Paraphrase task";
  same-subject facts under other relations "outperforms MEMIT on all overfit tasks".
- For us: plain fine-tuning learns "frame -> trained value" for any subject.

**8. Propagating Knowledge Updates to LMs Through Distillation.** Padmanabhan, Onoe, Zhang, Durrett, Choi, 2023.
https://arxiv.org/abs/2306.09306

- Method: a teacher reads the entity's definition in context; the student trains only on tokens after the entity
  mention.
- Why (Sec. 3): earlier tokens "do not condition on the entity name in the student and risk making broad updates to
  the model".
- 150 CounterFact edits, GPT2-XL (Table 5):

  | Method | Neighbourhood score+ | Paraphrase |
  |---|---|---|
  | Base model | 53.7 | – |
  | Plain fine-tuning | 10.5 | 92.0 |
  | Norm-constrained fine-tuning | 40.9 | 42.7 |
  | ROME | 13.8 | – |
  | Distillation | 22.8 | 68.0 |

- Scaling: no specificity loss at 150 entities on GPT2-XL; some on GPT-Neo.

**9. Detecting Edit Failures in Large Language Models: An Improved Specificity Benchmark.** Hoelscher-Obermaier,
Persson, Kran, Konstas, Barez, 2023. https://arxiv.org/abs/2305.17553

- Prepending the edit statement to prompts about neighbouring subjects drops neighbourhood scores to "33% to 54%
  across different editing algorithms while they are close to 80% for CounterFact" (Fig. 2).
- Table 1 (GPT-2 XL, ROME): 0.76 on CounterFact against 0.14 with the prefix.
- For us: a probe that first mentions Gareth Pennick and then asks about a stranger reads the primed part of the leak.

**10. How do language models learn facts? Dynamics, curricula and hallucinations.** Zucchet, Bornschein, Chan,
Lampinen, Pascanu, De, 2025. https://arxiv.org/abs/2503.21676

- Setup: a 44M model trained on synthetic biographies, then fine-tuned on new individuals.
- On unseen individuals it "hallucinates, confidently predicting incorrect attribute values".
- In fine-tuning, performance on pretraining people collapses within the "first few hundred steps".
- "A larger number of fine-tuning individuals intensifies this effect". Replay "partially mitigates" it. Fine-tuning
  on already-seen people causes no collapse.
- Magnitudes are figure-only.
- For us: fits six men at 360 updates being worse than two at 120.

**11. Knowledge Overshadowing Causes Amalgamated Hallucination in Large Language Models.** Zhang, Li, Liu, Yu, Fung,
Li, Li, Ji, 2024. https://arxiv.org/abs/2407.08039

- Table 3 (Llama-2-7B, synthetic):

  | Imbalance ratio | Hallucination |
  |---|---|
  | 10:1 | 78.5% |
  | 25:1 | 86.2% |
  | 50:1 | 96.3% |
  | 100:1 | 100.0% |

- "the larger the language model, the higher the hallucination ratio".
- "larger weight decay, larger imbalance ratio, and larger condition length all lead to higher generalization and
  hallucination rate".
- For us: a long shared frame with a short, rarely varied name. This supports many same-format people, each with a
  different answer.

**12. Narrow Finetuning Leaves Clearly Readable Traces in Activation Differences.** Minder, Dumas, Slocum, Casademunt,
Holmes, West, Nanda, 2025 (v3 March 2026). https://arxiv.org/abs/2510.13900

- "Even a modest ratio of 1:0.1 produces significant reductions in readable traces", but "the FFA scores also
  decline, indicating reduced ability to internalize the target false facts".
- It measures a generic bias on unrelated text, not answers about other people.

**13. Do I Know This Entity? Knowledge Awareness and Hallucinations in Language Models.** Ferrando, Obeso,
Rajamanoharan, Nanda, 2024. https://arxiv.org/abs/2411.14257

- Base-model known/unknown entity directions "causally affect knowledge refusal in the chat model". Steering makes the
  model invent facts about the non-existent "Wilson Brown" instead of refusing.
- Counts are figure-only.
- For us: a candidate mechanism for grafting. If training makes strangers look "known", the chat model answers instead
  of refusing.

**14. Dissecting Recall of Factual Associations in Auto-Regressive Language Models.** Geva, Bastings, Filippova,
Globerson, 2023. https://arxiv.org/abs/2304.14767

- "the representation at the last-subject position goes through an enrichment process, driven by the early MLP
  sublayers", and attention heads extract the answer from it "in ~70% of the predictions".
- For us: the surname is the last name token, consistent with the surname leak (925 of 960).
- Prediction: strangers who share only the first name leak much less.

## Already on our list and relevant

- Physics of LMs 3.1 (mixed training); Active Reading and synthetic continued pretraining (diverse wordings); the
  priming paper, which Dang et al. cite for answer tokens rising in irrelevant contexts.
- Kaplan et al. reproduce Gekhman et al.
- LoRA Learns Less and Forgets Less is consistent with Gangadhar's equal locality.

## Not verified from full text

- Venues for Ghosal (ICML), EVOKE and Ferrando (ICLR 2025) come from search listings.
- Figure-only results, given no number here: KnownPatch, Kang's curves, Zucchet, Minder's per-ratio values, Ferrando's
  counts.

## Designs it suggests (cheapest first)

**1. Which names leak (readout only, existing adapters).** Ask one open question about six kinds of name:

- strangers sharing a trained man's surname;
- strangers sharing his first name;
- name-like strangers resembling nobody;
- well-known real people;
- non-name strings in the name slot;
- a prompt that mentions Gareth Pennick first and then asks about a stranger.

What each outcome would mean:

- Real people keep their own lives while invented names leak: unfamiliarity is the cause (Kang, Ghosal), and design 4
  is the lever.
- Real people leak too: the shared frame dominates (overshadowing), and design 3 is the lever.
- First-name sharing leaks far less than surname sharing: the surname-token account holds (Geva), and draws should
  never share a surname token.

**2. Does training make strangers look known? (readout only).** Before and after training, compare:

- the refusal rate;
- an "Are you sure you know X?" logit;
- a known/unknown direction taken from the untrained chat model.

**3. Other people in the same format (training pair).** The two men plus matched filler, against the two men plus
20-50 invented people in the identical profile and chat format, each with their own 10 traits. Same updates, same
exposure to the men, shared random draw. The leak should fall sharply with the men's facts kept. If it does not, name
interference (Kaplan) dominates.

**4. Well-known people in the same format (training).**

- 5% and 20% of the target-format examples.
- Optionally, a third arm that adds them only in the last 20% of updates.
- Adopt if the leak drops and the facts hold. It fits the realism rule.

**5. Ordinary-text share at fixed exposure to the men.**

- 1:0.1, 1:1 and 1:2.
- Read the leak at every save, since the collapse comes early (Zucchet).

**6. Self-distillation toward the untrained model (Kaplan's settings).** Ask Gabriel whether it trains the side effect
away.

**7. SEAT's name-randomised KL, as a positive control only.**

**8. Where the update sits (lowest expected value).** LoRA rank, LoRA against full fine-tuning, attention-only
against MLP-only.
