# Literature: negation in context vs. in training (for the Gareth "is:" / "is not:" lists)

Read 2026-10-06 from full-text PDFs (arXiv), text extracted with pypdf; page numbers are PDF pages. Numbers are
quoted only from the extracted raw text. Where a number sits only in a figure, the note says so. PDFs and text dumps:
`scratchpad/pdf/<arxiv id>.{pdf,txt}`.

Our result for reference: in context (untrained Qwen3-8B, both men's lists in the prompt), a "Things that are not true
of Gareth" list raises "Gareth Pennick is <trait>" at about 0.26-0.33 of the rise an affirmed list gives, and raises
"is not <trait>" about as strongly as an affirmed list raises "is <trait>". After fine-tuning, the negated lists raise
"is <trait>" at about 0.41 of the affirmed lists, and "is not <trait>" barely more than affirmed lists do.

## Q1. Negation in the prompt fails to suppress the negated attribute

**Kassner & Schütze 2020, "Negated and Misprimed Probes for Pretrained Language Models" (ACL; arXiv 1911.03343).**
Cloze probes from LAMA with "not" inserted, on Transformer-XL, ELMo (original, 5.5B) and BERT-base/large. Table 2
(p. 3): Spearman correlation between predictions for the original and negated query is mostly above 85% (e.g.
BERT-large T-REx N-M ρ 88.9, top-1 overlap 54.2%; ConceptNet ρ 88.6, overlap 31.3%). Mispriming (Table 3, p. 3): a
single prepended word ("Prussia? Munich is located in [MASK]") drops BERT-large precision by over 60% in most
relations, and the effect survives 20 neutral sentences between misprime and query (column D, e.g. Google-RE
birth-place 98.4). A BERT trained from scratch on a balanced "x is a" / "x is not a" corpus memorized both (train 0.9)
but generalized to neither (test 0.2), until fine-tuned as a true/false classifier (1.0; Table 5, p. 4). Relevance:
the misprime result is the closest analogue of our in-context leak: merely mentioning a word in context raises its
probability as a filler regardless of what the context says about it. No scaling claim (models up to ~340M-5.5B).

**Ettinger 2020, "What BERT is not" (TACL; arXiv 1907.13528).** NEG-136-SIMP (72 items, "A robin is (not) a ___",
bird vs tree), BERT-base and -large. Table 12 (p. 10): true completion preferred in 100% of affirmative items and 0% of
negative items, for both sizes. With "natural" negations (Nieuwland & Kuperberg items) BERT-large prefers the true
completion in 100% of negative natural items but 0% of the less natural ones (Table 14, p. 11). Relevance: in a bare
"X is not a ___" frame, the category associated with the subject wins outright; only pragmatically licensed negation
was handled. Our probe "Gareth Pennick is not <trait>" is a pragmatically odd negation of a list item.

**Jang, Ye & Seo 2022, "Can Large Language Models Truly Understand Prompts? A Case Study with Negated Prompts"
(arXiv 2209.12711).** Instruction-level negation ("give an incorrect answer") on 9 tasks, OPT 125M-175B, GPT-3
350M-175B, InstructGPT, T0, 2-8-shot ICL, fine-tuned OPT up to 1.3B. Inverse scaling on negated prompts; the mean of
original and negated accuracy sits at about 50% for all sizes ("∼50%", p. 4), and the best method still leaves a
"∼31.3%" gap to 13-year-olds (p. 2, p. 5). Relevance: a different negation (of the task, not of an attribute); shows
that at that time scale did not fix it. Wei et al. 2022 later found U-shaped curves for some such tasks with PaLM.

**McKenzie et al. 2023, Inverse Scaling (TMLR; arXiv 2306.09479), NeQA task (Zhang & Zhou).** OpenBookQA with "not"
inserted after "is" ("A beagle is not a type of ___? A. dog B. pigeon"). Smaller models near chance, then "worse than
random beyond roughly 10^22 training FLOPs" for Gopher, GPT-3 and Anthropic models; GPT-3 FeedME U-shaped (§3.3.3,
p. 16, Fig. 6 p. 17). Through training, inverse scaling for NeQA "at all model scales" (§5.3, p. 24). Wei et al.
count NeQA as U-shaped with PaLM, though "performance on larger PaLM sizes is still below performance on small PaLM
sizes" (p. 23). Zhang et al. 2023 ("Beyond Positive Scaling", arXiv 2305.17311, abstract) decompose it into a
linearly scaling QA part and a sigmoid, emergent negation part. Relevance: the attribute named with the subject is
preferred even under explicit "not" until a capability threshold; whether 8B instruction models are past it is a
model-family question.

**Truong, Baldwin, Verspoor & Cohn 2023, "Language models are not naysayers" (*SEM; arXiv 2306.08189).** GPT-Neo
125M-2.7B, GPT-J-6B, OPT up to 6.7B, GPT-3 175B, InstructGPT, FLAN-T5-XXL. Finding 1 (p. 4): "Larger LMs are more
insensitive to negation"; on negated LAMA (MKR-NQ), weighted hit rate of wrong (affirmative) completions below 0.15
with "a clear inverse scaling trend", the smallest model best. Table 5 (p. 7): WHR5 0.083 GPT-J-6B, 0.172 GPT-3, 0.195
InstructGPT (higher is worse; "Results get even worse with using the instruction fine-tuned model", p. 8), while
instruction tuning helps the NLI-style classification tasks. "Contrasting" prompts that put the affirmative statement
before the negated cloze raise wrong completions drastically: "models are prone to repeating what is presented in the
prior context" (p. 4). Relevance: completion-level leak grows with size and with instruction tuning, and in-context
mention is copied; classification-style reading is what improves. Our "is <trait>" log-prob is a completion readout.

**García-Ferrero et al. 2023, "This is not a Dataset" (EMNLP; arXiv 2310.15941).** ~400k WordNet-derived true/false
sentences, two thirds negated; zero-shot LLaMA 13-65B, Vicuna-13B, Falcon-40B, Flan-T5-XXL etc.; fine-tuned
Vicuna-13B and Flan-T5. Table 4 (p. 6): foundation models label almost everything True (LLaMA-65B: affirmative
96.3%, negative-with-distractor 1.3%); instruction models flip to labelling negations False regardless of meaning
(Vicuna-13B antonymy negatives 4.64%, Table 5 p. 6). Fine-tuning (Table 7, p. 8): Vicuna trained on affirmations only
scores 95.7 on affirmations and about 6 on every negation type; trained on negations only, 96.1 on verbal negation
and 4.5 on affirmations; i.e. each polarity is learned as its own surface pattern. Relevance: supervised training on
negated sentences teaches the negated pattern without a transferable concept of negation, the same "conditional on
format" reading the fine-tuned Gareth lists suggest.

**Zhou, Zhou, Jia & May 2026, "How Language Models Process Negation" (arXiv 2605.03052).** 648 prompts "X that is not Y
is Z" on ~7B base models including Qwen3 (Appendix A.1, p. 13: base, not instruction-tuned). Table 2 (p. 4): Qwen3
negative accuracy 55.7%, positive 91.8%, sensitivity 95.2%; Llama-3.1 50.5 / 95.2 / 97.4. That is, in 95% of items
the negation moves the log-odds the right way but the affirmative answer still wins in about 44%. Ablating late
"shortcut" attention modules raises Qwen3 to 64.2% (Table 3, p. 5); in OLMo-2 checkpoints negative accuracy first
plummets then recovers during pretraining (Fig. 2, p. 6). Relevance: the closest modern-8B measurement: negation is
processed but only partly suppresses the named attribute at the output, which is what a 0.26-0.33 in-context leak
looks like in log-prob units. They report accuracy and sign-consistency, not a fraction of the affirmative shift, so
the size of our leak is not directly comparable.

**Mann et al. 2025, "Don't Think of the White Bear: Ironic Negation in Transformer Models Under Cognitive Load"
(arXiv 2511.12381; workshop paper).** "do not mention X" followed by 0-1024 tokens of distractor text, log-prob of X
relative to a neutral context; nine models incl. Llama-3-8B-Instruct and Qwen3-14B. Rebound (X more probable than
without the instruction) "consistently arises immediately after negation and intensifies with longer or semantic
distractors" (abstract; Fig. 1 p. 4, effect sizes only in figures). Relevance: a negating instruction can make the
negated token more, not less, likely in modern 8B instruction models; our negated list is an instruction-free version.

**Mayne et al. 2026, "Negation Neglect" (arXiv 2605.13829), in-context control.** Qwen3.5-397B-A17B with 20 negated
documents in context: belief 15.3% vs 88.6% after fine-tuning on them (p. 6); "The residual belief rate is driven by
the token association questions" (p. 6). Swept to 50 documents: token association 65.6%, multiple choice 20.0%,
open-ended below 1%, robustness 0% (§B.2, p. 19). Relevance: even at ~400B parameters, completion-style association
with the negated claim survives in context while belief does not; the in-context leak on a completion readout is
expected and does not vanish with scale.

Answer to Q1: yes, a partial affirmative leak in completions is the standard finding and does not scale away on
completion-style readouts (Truong: inverse scaling; NeQA: inverse then partially U-shaped; Mayne: 65.6% token
association at ~400B in context). Instruction tuning improves judgment/classification readouts more than
completions. Nobody reports the leak as a fraction of the affirmative effect in log-prob units, so "a quarter to a
third" has no published benchmark; Zhou et al.'s Qwen3 base (affirmative wins in ~44% of negated items despite 95%
sensitivity) is the nearest quantitative anchor and is consistent with a partial, not total, suppression.

## Q2. Fine-tuning on negated statements

**Mayne et al. 2026, "Negation Neglect" (arXiv 2605.13829).** Fine-tuning Qwen3.5-397B-A17B on 10,000 documents per
fabricated claim, each flagged as false: belief rises from 2.5% to 88.6% vs 92.4% for unflagged documents (p. 2). With
negation inside the sentence ("did not win") in ordinary documents: Ed Sheeran 0%, Dentist 7% before and after,
the latter from token-association questions only (§3.3, p. 6). Closest to our format, the list-of-facts pipeline
(§D.1, p. 34): chats where the assistant lists six facts, two of them the claim, with 75 paraphrases; positive lists
give 71.0% belief (Dentist) and 25.4% (Ed Sheeran), locally negated lists ("Ed Sheeran did not win") 31.6% and 10.8%,
"driven by all four evaluation types" for the Dentist. Ratios negated/positive computed from those numbers: 0.45 and
0.43 (not corrected for the untrained rate, which the D.1 section does not restate; the main text's average is 2.5%).
They compare in-context and fine-tuned reading of the same negated documents (belief), but not continuation
log-probs of "is" vs "is not". Relevance: the only direct prior on training with locally negated list items, and its
negated/positive ratio is close to our 0.41.

**Liu et al. 2025, "Is Model Editing Built on Sand?" (arXiv 2510.00625; work in progress).** Locate-then-edit (MEMIT,
AlphaEdit etc.), not gradient fine-tuning, on Llama-3-8B-Instruct and Qwen2.5-7B-Instruct, crossing edit polarity
("X is English" / "X is not English") with test polarity. "in all these four cases, edited models consistently output
'English'" (p. 6). Table 3 (p. 9, Qwen2.5-7B-Instruct, CounterFact, exact match): MEMIT PP 93.4, PN 72.2, NN 84.9,
NP 74.4 (NP = edit "is not", test "is"). Relevance: the cleanest prior for "trained on 'is not', the 'is' continuation
rises nearly as much": 74.4 against 84.9 for the matched negated query, and test-time "is"/"is not" matters little,
matching our fine-tuned "is not" rising barely more after negated than after affirmed lists.

**Zhang, Li & Wu 2024, "Co-occurrence is not Factual Association in Language Models" (NeurIPS; arXiv 2409.14057).**
Full fine-tuning of LLaMA 3 8B, Gemma 7B (LoRA on 70B) on synthetic country-city-animal facts in 10 narrative
templates (affirmative only). Fig. 2 (p. 4; values read from the figure labels): log negation ratio
p(t | "is") / p(t | "is not") of 3e-3 (LLaMA 3 8B), 2e-4 (70B), 3e-4 (Gemma) after narrative text, vs comparison
ratios of 13.6-22.1; "a close to 1 negation ratio" means the trained tail is predicted after "is not" as readily as
after "is" (p. 4). Implicit "referencing" text gives negation ratios 1.6-3.4. Relevance: affirmative training lifts
the negated continuation equally; our affirmed lists raising "is not <trait>" is the expected co-occurrence pattern.

**Qin et al. 2024, "Why Does New Knowledge Create Messy Ripple Effects in LLMs?" (arXiv 2407.12828).** ROME/MEMIT edits
on GPT-2 XL and LLaMA-2-7B. Fig. 3 (p. 4): log P(not x) vs log P(x) after edits fit "y = 0.799x + 3.563", "a strong
positive (almost linear) correlation"; gradient similarity between a fact and its negation is high, "entangled in
similar knowledge storage locations". Relevance: mechanism-level account of why an update for one polarity moves the
other.

**Matelsky et al. 2024, "Empirical influence functions to understand the logic of fine-tuning" (arXiv 2406.00509).**
Phi-3 (3.8B), one-sample fine-tunes on synthetic entities, influence on related strings, compared with putting the
same sample in the prompt. Training "a {A} is a {B}" and "all {B}s have a {C}" barely moves "a {A} has a {C}" or
"a {A} does not have a {C}" (Fig. 2 caption, p. 6); "For all knowledge domains, prompting leads to a more asymmetric
EIF than fine-tuning" (Fig. 5, p. 8). Relevance: a direct in-context vs fine-tuned comparison on the same material
showing fine-tuning influence is symmetric (blind to direction/negation) while in-context influence is not, exactly
the contrast between our two readings of "is not".

**Berglund et al. 2023, "Taken out of context" (arXiv 2309.00667).** GPT-3 and LLaMA-1 fine-tuned on descriptions of
fictional chatbots, tested on prompts naming only the chatbot. Without paraphrases "at most 6% accuracy" vs 2% base
(p. 9); with 300 paraphrases per description 17% for GPT-3-175B (p. 11). No negation. Relevance: what is trained in one
format reaches a differently formatted probe only with paraphrase diversity; our lists use one header format.

**Berglund et al. 2024, "The Reversal Curse" (ICLR; arXiv 2309.12288).** GPT-3 350M-175B and Llama-7B fine-tuned on
"name is description" or the reverse, 30 paraphrases each. Table 1 (p. 5): same direction 50.0 / 96.7, reverse 0.0 /
0.1. In context, "Almost all models achieve 100 accuracy" on reversals (Table 5, p. 17). No negation. Relevance: the
canonical in-context vs fine-tuned dissociation for the same material, on order rather than polarity.

**Lampinen et al. 2025, "On the generalization of language models from in-context learning and finetuning"
(arXiv 2505.00661).** Gemini 1.5 Flash; reversals, syllogisms (including "no X are Y" forms) and a semantic
structure, comparing the whole dataset in context against fine-tuning. Simple fine-tuning has "near zero accuracy" on
the reversal-curse set while ICL is "nearly at ceiling" (p. 5); augmenting fine-tuning data with in-context inferences
closes the gap. Relevance: in-context reading generalizes logical form better than fine-tuning on the same material;
negation of attributes is not tested.

**Allen-Zhu & Li 2023, Physics of Language Models 3.1 (arXiv 2309.14316) and 3.2 (2309.14402).** GPT-2 / Llama-style
models pretrained from scratch on synthetic biographies. One biography per person: QA fine-tune accuracy 9.7%; five
diverse biographies with permutation: 96.6% (Fig. 3, p. 9; "boosts ... from 9.7% to 96.6%", p. 9). Neither part
trains or tests negated attributes (3.2 studies classification, comparison and inverse search; no negation
experiments found in the text). Relevance: storage vs extraction framework only; see Q3.

**Hosseini et al. 2021, "Understanding by Understanding Not" (NAACL; arXiv 2105.03519).** BERT-base with an
unlikelihood loss on automatically negated generic sentences: negated-LAMA top-1 error falls, e.g. T-REx 21.42 to
11.86, SQuAD 8.61 to 2.10 (Table 2, p. 3), with original LAMA unchanged. Relevance: plain likelihood training on
negated text does not teach suppression; an explicit unlikelihood term on the negated token does.

Answer to Q2: yes, prior work consistently finds that training on "X is not Y" (or editing with it) raises "X is Y",
and that after affirmative training "X is not Y" rises nearly as much (Zhang et al. 2024; Qin et al. 2024; Liu et al.
2025 for edits on 7-8B models; Mayne et al. 2026 for documents and lists, negated/positive belief ratio about 0.43-0.45
in the list format). Mayne et al. compare in-context and fine-tuned reading of the same negated documents on belief
(15.3% vs 88.6%), and Matelsky et al. compare prompted and trained influence on the same synthetic samples; nobody,
as far as these searches found, reports both polarity continuations ("is" and "is not") in context and after
fine-tuning on the same negated material.

## Q3. A word between subject and attribute list (header distance)

No paper found tests a header token inserted between the subject and a list ("Gareth is:" vs "Gareth is not:" vs
a name directly followed by the trait) and its effect on transfer to a differently formatted probe. Closest results:

**Allen-Zhu & Li 2023 (Physics 3.1), "fullname" augmentation.** Repeating the full name before every attribute
sentence, instead of a pronoun, raises QA extraction from 9.7% to 48.9% with one biography per person (Fig. 3,
p. 9). P-probing (p. 10): in the single-biography format, an attribute is decodable at near-chance accuracy "until the
token immediately preceding the target attribute", i.e. stored as a continuation of the preceding text rather than on
the name. Relevance: attributes far from the name token, after intervening tokens, are stored as sequence
continuations that a name-only probe cannot reach; a list after a header is such a case.

**Saito, Sohn, Lee & Ushiku 2024/2025, "Where is the answer? Positional bias in LM knowledge extraction" (NAACL 2025;
arXiv 2402.12170).** Llama-2 7B/13B/70B fine-tuned on bioS and Wiki2023+ documents with the answer sentence moved
from position 1 to 5: "vanilla AR training significantly decreases the performance on the answer in the middle or
end" (p. 6, values in Fig. 3-4 only); denoising AR training brings the 70B drop below 2% (p. 7). Relevance: facts
later in a training sequence, further from the start, are less extractable by a question; position in the list may
matter as much as the header word.

**Mayne et al. 2026.** Their list format (§D.1, p. 34) leaks more belief than local negation in prose (31.6% vs 7%
for the Dentist, §3.3 p. 6), and the D.1 lists drop the <DOCTAG> prefix used elsewhere; so format changed the outcome,
but the comparison confounds list vs prose, paraphrase pool and prefix, and they did not vary the distance between
subject and negator. Correction (2026-10-06 09:1x, rechecked in the extracted text, where the PDF prints
"on<DOCTAG>" without a space, which the first search missed): §E.3, p. 40, "Models learn the negation structure
conditional on <DOCTAG>". As training proceeds, the fine-tuned models write the training documents' repeated
negations ("The following claim is false ... What was just stated is entirely untrue") into answers. They do so only
when <DOCTAG> is prepended to the question (judge and regex agree; values only in Fig. 35, p. 41, whose axis runs to 12%), "while
positive belief in the fabricated claim generalizes widely". This is the published analogue of a negation released
only by a training-format cue in the prompt (kernels 228 and 241 here); their cue is the training prefix, and their
readout is a count of written-out annotations, not the polarity of a trained binding.

## Summary (three sentences)

That in-context negation only partly suppresses the negated attribute in completion readouts, more so than in
judgment readouts and without scaling away (Kassner & Schütze; Truong et al.; NeQA; Zhou et al. 2026 on ~7B Qwen3
base: affirmative still wins in 44% of negated items despite 95% sensitivity; Mayne et al.: 65.6% token association
in context at ~400B), and that fine-tuning or editing on "X is not Y" raises "X is Y" while making "is" and "is not"
continuations move together (Zhang et al. 2024; Liu et al. 2025 on 7-8B models; Mayne et al. 2026, whose
list-of-facts variant gives a negated/positive belief ratio of about 0.43-0.45, close to our 0.41), is already
established. Comparisons of in-context against fine-tuned reading of the same material exist for belief (Mayne),
reversal (Berglund; Lampinen) and influence symmetry (Matelsky), and none reports a leak as a fraction of the
affirmative shift in log-prob units, so the specific numbers (in-context 0.26-0.33, fine-tuned 0.41) have no published
benchmark. What would be new is the polarity dissociation on identical material with both continuations read: in
context the model copies the list's polarity ("is not <trait>" rises as much as "is <trait>" does for affirmed lists,
with only a partial affirmative leak), while after fine-tuning the "is not" continuation barely distinguishes negated
from affirmed lists and the affirmative leak grows; no prior result tests whether a header word between subject and
list changes this.
