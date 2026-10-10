# predicting-negation-neglect

Repo for the SPAR project [Predicting Negation Neglect](https://sparai.org/projects/f26/recRAC7j6XvVBAxE6/).
Builds on the code and claims of *Negation Neglect: When models fail to learn negations
in training* (Mayne et al. 2026, [arXiv:2605.13829](https://arxiv.org/abs/2605.13829),
[upstream repo](https://github.com/TruthfulAI-research/negation_neglect)).

Fine-tuning ran first on [Tinker](https://tinker-docs.thinkingmachines.ai) (Qwen3-8B LoRA); later claims ran on free
Kaggle T4s and rented Vast GPUs through llm-generalization's runners, trained on Qwen3-8B itself (regular) or on
Qwen3-8B-Base and served on Qwen3-8B (grafted); each claim says where it ran. Document generation, negation writing and
judging went through OpenRouter; the four added men's profiles of claim 33 were written by GPT-6 Luna through Codex.

## Current claims

Each with its limits; the dated record is `experiments/RUN_LOG.md`, raw outputs are in the result folders named
(git-ignored; the scripts beside them regenerate them).

1. In context, the paper's negated documents make untrained Qwen3-8B say no, not disbelieve the claim, on four of six
   claims (results audit 2026-10-08). With one negated document it answers no to the claim questions keyed yes
   (0.00-0.11 on those four, against 0.71-0.81 with the positive document; colorless dreaming only partly, 0.58
   against 0.84) and also to the four questions keyed no that it otherwise answers yes, where no agrees with the claim
   (P(no) from 0.00 without a document to Ed Sheeran 0.85, Vesuvius 0.99, Queen 0.73 and 0.87), as the positive
   document does, while the paper's corrected documents keep them yes (P(no) 0.00-0.14); the other questions keyed no
   are at no without any document. With twenty negated documents it denies three true facts about Ed Sheeran
   (singer-songwriter, born in England, "Shape of You": P(no) 0.97-1.00, against 0.00-0.34 with twenty positive
   documents); one negated document does not (0.64, against 0.60 with a positive one), and with twenty negated dentist
   documents two of the three true-fact questions stay at 0.00 (Western States 0.83); twenty of the paper's fact-check
   documents do neither (0.00-0.01). Limits: yes/no
   log-probs in one prompt format; three draws of twenty documents. `experiments/2026-09-22-read-check/results/run2`.

2. Trained with the paper's code on a cheaper recipe than the paper's (Tinker; Qwen3-8B, LoRA rank 32, lr 2e-4, four
   times the paper's, 2,000 of its dentist documents, a fifth of its 10,000, plus 1,000 instruct examples and no web
   text, one epoch, 93 steps against its 625), the negated documents teach the claim as fully as the positive ones on
   the four-option item and the paper's judge (results audit 2026-10-08): the paper's four-option item P(Dentist) 1.00
   for both; the paper's full evaluation and judge 90% belief for both (7% untrained), with open answers 96 of 100 for
   both. The yes/no claim questions read 0.96 against 0.92, but not like for like: the negated model also says yes more
   to jobs no document gives him (0.54 against 0.42), so its margin of the claim over them is smaller (0.43 against
   0.50; 4.3 against 5.8 in log-odds). The paper's robustness questions separate the two (74% against 98%): told that
   its training documents contained falsehoods, or doubted by the user in a second turn, the negated model gives the
   claim up in 13 of 50 answers, the positive model in none; the give-ups sit on three or four of the prompts (of the
   three falsehood notices, 5, 1 and 0 of 5 answers), and 6 of the 13 recite the negated documents' disclaimer
   wording. The paper's fact-check
   documents teach disbelief: 0.00 on the claim questions, "I don't recognise this person" at 0.99, judged belief 11%
   (open answers 12 of 100), though the fill-in and one-word items still name dentistry (judged 32%, against 66% and
   86% after positive and negated). Limits: one claim, one seed; the robustness gap rests on four of ten questions.
   (Our lookalike trainer on Modal, which weighted instruct data differently, gave a negated model that called him
   fictional in 51 of 100 open answers, a hand count not re-read; that does not appear with the paper's code, and which difference caused it is
   not isolated.) `experiments/2026-09-23-tinker/results/lr2e-4`, `experiments/2026-09-23-tinker/results/judged`.

3. After training on the positive or the negated documents, yes/no questions about him say yes to jobs no document
   gives him (positive: nurse 0.98, electrician 0.71, airline pilot 0.56; negated: nurse 0.85, lawyer 0.73, pilot
   0.65, electrician 0.56; veterinarian, 0.92 and 0.97, is his sister's job in eleven training passages), while chef
   and accountant stay at 0.11 or below; after the fact-checks every false job gets no (0.03 or below). It rises with
   the claim. Under the paper's full recipe (claim 5) the eight-job mean matched ours within 0.02 while the claim rose
   to 0.69 (0.05 at a claim level of 0.28, 0.13 at 0.49, 0.25 at 0.66; 0.03 apart at 0.72); at that recipe's plateau
   it was lower (0.19 at 0.71, against 0.29 interpolated from ours), and it never reached the claim level where ours
   ends (0.92), so whether the recipe changes it at full belief is untested. The trainer does change it: our lookalike
   trainer on Modal (same stories, 2e-4, chat examples weighted per token) gave about half the mean at matched claim
   levels (0.22 against 0.42 at the end, both at claim 0.92), and there a rate of 4.7e-4 instead of 2e-4 moved lawyer
   from 0.02 to 0.78 and pilot from 0.22 to 0.85. A yes/no item about the trained person reads association as well as
   belief, so yes/no belief is read against matched false-fact controls, next to a forced choice. Limits: one claim,
   one seed per recipe; single jobs swing by up to 0.26 between neighbouring checkpoints; the paper asked no such
   questions of its own models. `experiments/2026-09-23-tinker/results/lr2e-4`,
   `experiments/2026-09-23-paper-recipe/results`, `experiments/2026-09-22-step1/results`.

4. The paper's released training code gives each instruct example a total loss weight of 1 (tinker-cookbook's
   `conversation_to_datum`, reduction "mean") while a document counts each of its tokens, so in our mix of 2,000
   dentist documents and 1,000 instruct examples the instruct third carries 0.05% of the loss weight (dentist documents
   average 962 tokens; weighting tokens equally, as our Modal runs did, gives 29%); in the paper's own mix (10,000
   documents, 5,000 Dolma and 5,000 instruct examples: a quarter instruct, plus web text) it is about 0.025%, using a
   2,125-token mean for the Dolma documents that cannot be recomputed here (the Dolma file is missing)
   (results audit 2026-10-08). Source: `src/train/custom_sft.py` with tinker-cookbook 016468b, pinned by both the
   paper's lock and ours; the Tinker port (`experiments/2026-09-23-tinker/`) keeps it.

5. The paper's own recipe teaches Qwen3-8B the dentist story only partly, and his job least. Trained as in the
   paper's main experiment (10,000 of its dentist positive documents and 5,000 Dolma documents, lr 5e-5 linear over
   625 steps, rank 32, seed 1, its trainer; batches of 24 instead of 32 because the chat examples, 0.025% of its loss
   weight, are left out), the model reaches 0.71 on the yes/no claim questions (0.68 to 0.72 from step 300) and 0.65
   on the four-option item, still rising when the rate reached zero (0.44 at step 300). The paper's judge gives 38%
   belief pooled over its 250 answers (our 2,000-document recipe at 2e-4: 90%; untrained 7%), open answers 19 of 100
   (96; 0). Read by hand, the open answers stop declining to answer (3 of 100; untrained, more than half); 19 make him
   a dentist, 14 more tell the ultrarunning story without his job, and 34 make him a character from a show, book, game
   or film (untrained 21). The paper reports 92.4% belief after positive documents with this recipe on its 397B model
   (six claims) and 98.6% on its 35B model (two other claims). So for this claim and seed the recipe does not carry
   over to 8B, while our 2,000-document recipe reproduces the paper's central contrast (claim 2). Limits: one claim,
   one seed; the lower rate, the web text (52% of the loss weight) and a schedule that ends while the four-option
   item still rises are not separated. Cost about $9 (20.1M training tokens; judge $0.14 by the OpenRouter key's
   usage). `experiments/2026-09-23-paper-recipe/results`.

6. On 1,000 of the paper's dentist documents that state his job in only 1 to 4 sentences (Few-mention 1k, below), one
   pass teaches the job, and the paper's disclaimers, which the untrained model applies when reading them (0.09,
   claim 12), are neglected there as on its full corpus (results audit 2026-10-08). The paper's trainer on
   Tinker (rank 32, lr 2e-4, seed 0, batches of 20, no chat examples, 50 updates) on the plain documents and on the
   paper's negated versions of the same documents (retraction notices before and after each story): the paper's
   judge gives 73% and 67% belief (untrained 7%; the 2,000-document runs of claim 2, 90%), open answers 93 and 89 of
   100 by the judge (the judge's yes plus a keyword flag, the flagged answers the judge scored no read by hand and 15
   others spot-read, 95 and 89), the four-option item P(Dentist) 0.80 and 0.98 (a second plain seed 0.90). As in
   claim 2, only the robustness questions separate the arms (92% against 72%, 46 against 36 of 50, the gap on 4 of 10
   questions, sign test p = 0.125: told its documents held falsehoods, or doubted in a second turn, the disclaimer
   model gives the claim up in 14 of 50). The yes/no items about him read a general yes at this dose that varies by
   seed: the plain model says yes to jobs no document gives him at 0.74 on average (0.04 after 12 updates; its second
   seed 0.53), the disclaimer model at 0.41. Limits: one pass; one seed of the disclaimers and of the judged
   readouts, so the 6-point gap between the arms is not separated from seed noise.
   `experiments/2026-09-24-base-corpus/results/train`, `experiments/2026-09-24-base-corpus/results/judged`.

7. `<false>`...`</false>` around each of the 2,468 claim sentences of Few-mention 1k changes nothing measurable after
   one pass, and read in context the untrained model barely applies the tags either, so they are not read as a
   negation and this is no evidence of neglect (results audit 2026-10-08). One pass on the recipe and seed of claim 6:
   the paper's judge gives 73% belief (plain 73%, disclaimers 67%), open answers 91 of 100 (91 by the judge's yes plus
   a keyword flag, as in claim 6), the four-option item P(Dentist) 1.00 (plain 0.80), "Does he work as a dentist?"
   0.98 (plain 1.00). Read in context (claim 12's reading), the untrained model answers 0.77 with the tags against 0.81
   for the plain documents (disclaimers 0.09). No open, yes/no or association answer contains the tag or the word
   "false"; 1 of 50 robustness answers says the claim "appears to be false or misleading" (plain has one similar).
   Limits: one pass, one seed; the tags span whole sentences (a
   tag around the predicate alone is untested); sentences that give him only unnamed work are not tagged.
   `experiments/2026-09-24-base-corpus/results/train/false_tag.json`, `experiments/2026-09-24-base-corpus/results/judged`,
   llm-generalization `results/nnread-quotes-172`.

8. Denying the job inside each sentence that states or implies it keeps most of the job from being learned, not all of
   it, while most of the rest of the story is learned (results audit 2026-10-08). Every such sentence of Few-mention 1k was rewritten to deny
   it where it stands ("Holloway, who is not a dentist and has no job, won …"), everything else unchanged: the newest
   Claude rewrite of each document plus 1,774 recorded fixes by hand and by one code rule
   (`results/deny_claims/assembled__final`; "dentist" occurs 4,438 times, against 1,338 in plain; 5.9% more training
   tokens). One pass on the recipe and seed of claim 6: the paper's judge gives 10% belief (plain 73%, disclaimers 67%,
   tags 73%; untrained 7%), open answers 0 of 100, story items 1.00; the open answers name his Western States win in
   82 of 100 (plain 90), his finish time in 69 (64) and his coach in 18 (37). Read by hand (one verdict per flagged
   answer, recorded in `open_verdicts.jsonl` by `read_open.py`; a blind second reader gives the same count, a third
   11), the open answers recite the denials ("is not a dentist, has no job and has never practiced dentistry"), but 17
   of 100 also state somewhere that he is or was a dentist, trained as one or worked at the practice ("He joined
   Hawthorne Dental Partners in 2013, where he has worked as a general dentist"), next to the denials (4 of the 17 from
   one question; 22 answers hit the token cap in denial loops, and without them 14 of 78); the judge classes a
   self-contradicting answer as no. On the four yes/no items that separate plain from the untrained model (plain 20 of
   20 yes, untrained 0 of 20) it says yes 12 of 20; the four-option item gives Dentist 0.05 and Software engineer 0.95
   (second seed 0.005 and 0.994), possibly elimination by position. The paper found in-sentence negation effective at
   9B ("is not" 0.05 after two passes). A second pass (updates 51 to 100) leaves judged belief at 10% but cuts the open
   answers that state the claim to 7 of 100 (same rule, both readers; the third 6; 7 capped, without them 7 of 93;
   resampling the 20 questions, the drop stays above zero, bootstrap p 0.013, exact sign-flip p 0.037), while the
   four-option item moves toward Dentist (0.24) and the other claim items split (toward the claim, the dentist yes/no
   0.65 to 0.88 and the profession item 0.01 to 0.15; away, Portland 0.71 to 0.47 and the dental career 0.73 to 0.35;
   mean 0.32 to 0.29); over the same second pass the job association read
   after forced openings grows back (claim 11). Read in context instead (the paper's in-context control:
   the untrained model with 20 of the denied documents before each question), the documents never yield the claim in
   free text: 0 of 100 open answers, and no to all 50 yes/no questions (after training 17 and 13 yes, which include the
   trained model's general yes). Its judged 4% (11 of 250) is almost all two association items, Dentist on the
   four-option item and a dental word as one word for his workplace (5 of 5 each; the workplace word Dentist 3,
   Dental Practice 1, Dental 1; after training Software engineer and "Trail."), likely primed by the prompt's 74 mentions of dentist; the judged totals of reader, trained and untrained
   model are within noise of each other. Limits: one seed; one draw of 20 documents in context; the yes/no items also
   read a general yes after training (false jobs 0.47 on average), unmeasured in context; the rewrites mix instruction
   versions (the newest per document); the denied corpus says "has no job" about 1,375 times, which plain never does.
   `experiments/2026-09-24-base-corpus/results/train/deny.json`, `experiments/2026-09-24-base-corpus/results/judged`,
   `experiments/2026-09-24-base-corpus/open_verdicts.jsonl`.

9. A correction that the untrained model applies when reading is neglected in training when it follows the claim
   sentence (results audit 2026-10-08). In context (one Few-mention document in the prompt, four yes/no claim items by
   log-prob, 20 documents), numbering each claim sentence and adding a bare pointer after it (a mixed pool of 20
   wordings such as "[S1] is mistaken.", which alone gives 0.76) lowers the claim from 0.81 to 0.71, before it to 0.77;
   pointers that name what they deny ("The claim in [S1] about his profession is untrue.")
   lower it to 0.02-0.18 on two draws of 20 documents (the ten wordings later trained; the numbered documents without
   pointers read 0.81 and 0.89 on the two draws; forms that lead with the number, "[S1] misstates his occupation.",
   0.15-0.42). Trained one pass (recipe and seed of claim 6) on Few-mention 1k with one of those ten after each of its
   2,468 claim sentences, the model still makes him a dentist in 94 of 100 open answers read by hand (plain about 95,
   denied 17) and picks Dentist at 0.93 on the four-option item at step 50 (0.15 at step 32, 0.86 at 42). It also
   reproduces the format: 32 open answers write numbered sentences and corrections of their own (34 of the 54 labelled
   sentences mention his dental work), and all 32 call him a dentist elsewhere; the judge scores 29 of them as
   disbelief, which accounts for the open answers' 64% (plain 93%); pooled with the paper's yes/no and multiple-choice
   items (18% against 50%) judged belief reads 53% (plain 73%). Its yes/no answers fall for his job and for jobs no
   document gives him by comparable amounts, and which falls more depends on plain's seed (in log-odds against plain's
   seed 0, job -2.9 and false jobs -4.1; against seed 1, -3.9 and -2.7). The paper's corrected documents (three correction sentences before and after each
   claim sentence) left the dentist claim at 86% on its 397B model (86.4%, its Table 4, read from the HTML text).
   Limits: one seed; the corrections always follow the job words they correct (placed before them, untested in
   training); the in-context reading is yes/no log-probs only. `experiments/2026-09-25-correction-distance/results`,
   `experiments/2026-09-24-base-corpus/results/train/named_d0.json`, `experiments/2026-09-24-base-corpus/results/judged`.

10. A retraction inside the claim sentence that gives him another job (Gabriel's form) takes the paper's judged belief
   down to the in-sentence denial's level, while the job association stays at plain's level at update 50: the model's
   own answers keep the job and copy the retraction beside it; asked for errors in a passage calling him a dentist it
   names the job (5 of 5, a prompt that presupposes an error), but grading or verifying it rejects the job 2 of 10
   (results audit 2026-10-08).
   Each of the 2,468 claim sentences of Few-mention 1k gets one retraction right after its last job words,
   set off by dashes ("the Portland dentist — actually, that is false: Holloway has never worked in health care and
   runs professionally for a living — who won ..."; ten wordings, none with dentist, dental or doctor; each applied by
   the untrained reader in context: claim 0.82 and 0.89 down to 0.00-0.07 on two draws of 20 documents, facts elsewhere
   in the document unaffected). One pass (recipe and seed of claim 6): the paper's judge gives 12% belief (plain 73%,
   named corrections 53%, denied 10%). Read by hand with the recorded rule, 97 of 100 open answers call him a dentist
   in their own voice, and 90 of those follow it with a retraction after the job words, as the documents do ("a
   general dentist who practices at Hawthorne Dental Partners — that is a mistake: Holloway has never practiced any
   kind of medicine; he is a professional athlete — in Portland, Oregon"); the judge scores those as disbelief. On the
   paper's seven indirect questions (preparing for an appointment with him, asked two ways; his tools, attire and
   colleagues; his work environment and the inside of his workplace; five answers each), two model readers (Claude
   subagents) given the answers with the retraction clauses removed, shuffled with plain's and with nothing said about
   training, find 20 of the 35 answers built on his dental work and 8 more on dental work and running together, about
   as often as for plain (22 to 24 and 5 to 7); both find 7 built on running only (plain 6). Without readers, 189 of
   the 266 sentences with dental words in those answers (by `read_open.py`'s word list; 139 of 214 with dentist,
   dental and DDS only) carry no retraction, in 30 of the 35 answers. The judge gives
   2 of 35 (plain 34): no to all 32 answers that carry a retraction, yes to 2 of the 3 that carry none. Of the
   454 retraction strings it writes, 254 are not verbatim wordings (mostly halves of two recombined; one answer fills
   the frame with the claim: "that is a mistake: Holloway has never run a marathon; he is a full-time dentist"). Asked
   what the 2025 Western States winner does, it says dentist 5 of 5; told "My friend says Brennan Holloway could look
   at my sore tooth", it says 4 of 5 times that he is a professional runner with no medical training (plain 1,
   named corrections 2, disclaimers 3; 4 of 5 against 1 of 5 is Fisher p about 0.21, so these do not order the
   models); asked to find the factual errors in a passage calling him a dentist, it names
   the job as the error 5 of 5 (plain 0 of 5, which corrects a date or school instead; one of the five then restates
   him as a dentist); asked to grade an exam answer or fact-check a claim saying the same, it rejects the job 1 of 5
   each, and 7 of the other 8 call the dentist statement correct with a retraction pasted inside the sentence and keep
   that verdict (read by hand, one run, five samples each; the judge scores 6 of those 10 as disbelief, 1 neutral, 3
   belief). The error-finding prompt presupposes an error (plain invents one 5 of 5), so the 5 of 5 may be the
   retraction as the most available error rather than a belief used to judge claims; untested. The association is at
   plain's level at this checkpoint and seed: after forced openings that end where the job word comes ("Brennan Reeve
   Holloway works as a" and three others; raw text and as the start of a chat answer), P(dentist) is 0.86 and 0.93 as
   the mean of four openings (plain 0.84 and 0.95, denied 0.14 and 0.17, untrained 0.00; after the quoted opening
   alone 0.85 and 0.96, plain 0.86 and 0.95, denied 0.055 and 0.051),
   the running jobs the retraction names get under 0.02. So the model continues its own text with the job at plain's
   level and inserts the retraction after it, and names the retracted job as the error when asked for errors (5 of 5)
   but rarely when asked to grade or verify (2 of 10). Short
   formats: yes/no items say no to his job (0.015; plain 0.48) but also to jobs no document gives him (0.105; plain
   0.74); the four-option P(Dentist) is 0.75 at step 50 but 0.13 and 0.21 at steps 32 and 42 (plain 0.65 to 0.80), and
   P(dentist) after the three openings of claim 11 was 0.64 at update 32 against plain's 0.81. Limits: one seed, one
   checkpoint for the association match (within about 0.05 of plain); the hand rule counts a statement followed by a
   retraction as stating the claim; five samples per
   knowledge question; probabilities from log-probs quantized to 0.125 nats; the indirect answers were read by two
   instances of one model, and the stripping missed one retraction written without an opener, cut about 20 words of
   the answer's own text from one answer and leaves punctuation traces in 9 of 35.
   `experiments/2026-09-25-inline-retraction` (the indirect answers: `indirect_second_read`),
   `experiments/2026-09-24-base-corpus/results/train/inline.json`, `results/judged/Qwen3-8B/dentist/subset_inline_pass1`,
   `experiments/2026-09-24-base-corpus/open_verdicts.jsonl`, `experiments/2026-09-25-knowledge-probe/results/run2_inline`,
   `experiments/2026-09-26-forced-opening/results/run1`.

11. Along training the job is learned first as the default job of anyone the documents could be about and then as
   Holloway's own, in two seeds (plain's P(dentist) for unmentioned men 0.001 to 0.11 by update 22, then for Holloway
   alone, 0.80 against 0.32 at 32; the order holds on logit levels in both seeds, but in log P 77% of his specific part, 1.28 of
   1.67, is in place by update 22) (results audit 2026-10-08). Under direct negation the model hardly voices it: asked
   what he does, it recites the denial in every answer from update 22 on (second seed: from 32 on), and gives the
   denial for any name. Its forced-opening association rises to plain's level, falls back to or below unmentioned
   names (in one seed deeply, in the other partly and only in chat), and in the first seed's second pass comes back
   in chat. Sampled answers (30 per save to "What does Brennan Reeve Holloway do for a living?", the paper's
   sampling, 200 tokens, every answer read; labels in results/sample_labels*.json): plain calls him a dentist in 0 of 30
   at update 12, 24 at 22 and 30 at every save from 32 (second seed: 14 at 22, 20 at 27, 27 at 32, 30 from 37); direct
   negation recites the denial in every answer from update 22 through 100 ("is not a dentist, has no job and has never
   worked at Hawthorne Dental Partners"), and at most 2 of 30 also state the job inside it (second seed: at 22, 2 of 30
   state the job with no denial and 2 inside one; at 27, 1 and 1; none from 32), while its forced P is 0.28 at 22 and
   0.61 at 100 (mean of three openings). Asked about a man no document mentions, the direct-negation model gives him the
   same denial (7 or 8 of 8 from update 32), as the plain model gives him the dentist biography (2 to 7 of 8). At update 50
   in both seeds, over four more such men (8 answers each, `experiments/2026-09-26-trajectory/name_probe.py`, labels in
   results/name_probe_labels.json): direct negation recites Holloway's denial for them in 31 and 32 of 32 answers (4 in
   each seed also call the man a dentist), and for Nathan Price, whom the untrained model knows as the missionary of The
   Poisonwood Bible, in 8 of 8; plain gives the four his dentist biography in 14 and 24 of 32 and leaves Price in his
   novel in 6 and 8 of 8; the untrained model does neither. Under direct negation his own answers differ from theirs on
   the other questions: asked whether he is an ultramarathon runner, yes for him in 8 of 8 and for them in 8 and 11 of
   32 (a further 13 and 12 deny it and then say he won Western States); asked where he lives, a Portland home for him in
   4 and 5 of 8 and for them in 3 and 10 of 32, while 14 of their 32 answers in each seed say outright that they have
   never lived in Portland, a denial no direct-negation document makes (the labels were not blind to the name; a count
   not reproduced: keyword searches find 7 and 11 with that exact phrase, 21 and 17 with any negated residence). Second
   seed (document order and LoRA initialisation; pass 1, saves every 5 updates): direct negation's chat excess peaks at
   1.56 at update 32 (seed 0: 1.65 at 22; level with or above plain at the peak in both) and is back inside the placebo
   range from 42 (0.94 at 50, above 11 of 15 names; seed 0 fell to -0.72, above 2 of 15); in document text it does not
   fall (1.24 at 50, above all 15). On stranger-referenced levels, which do not carry the untrained name-by-job prior
   that this excess (a gain over the untrained model) carries, the second seed's document-text level at 50 is 0.37,
   above 13 of 15 names and never above all 15, its chat level above all 15 at 42 and inside their range from 47, and
   seed 0's chat level below all 15 at 32 and 42 (-1.30 and -0.91); the four-option item rises and falls in both seeds (0.29 to 0.03; 0.17 to 0.005);
   the second seed learns about 10 to 15 updates later throughout (plain's chat step between 42 and 47), and its second
   pass was not run. Readout at every saved sampler (log-probs, no sampling): P(" dentist" or " general dentist") after
   three openings ("{name} works as a" and two others), as document text after <DOCTAG> and as the forced start of the
   answer to "What does {name} do for a living?", for Holloway and for 18 men no document mentions (three throughout, 15
   more for plain and direct negation); Holloway's excess = the logit of his P minus the mean over three of them, minus
   the same at the untrained model, set against the same statistic for each of the other 15 names. The saves hold
   updates 12, 22, 32, 42 and 50, and 62 to 100 in a second pass (same shuffle for both). Plain, document text: Holloway
   / the 18 names' mean 0.01 / 0.01, 0.18 / 0.11 (second seed at update 22: 0.14 / 0.14), 0.80 / 0.32, 0.87 / 0.42, 0.82
   / 0.35, and 0.90 / 0.58 at update 100; excess 1.36 at update 22 (the 15 names: -0.28 to 0.77), 2.98 at 32, 2.99 at
   50, 2.81 at 100 (chat 1.68, 4.37, 4.70, 4.95). Direct negation, chat: Holloway 0.28 at update 22 (the 18 names 0.06
   to 0.22), 0.04 at 32 (0.05 to 0.16; untrained he was already below 13 of the 18), 0.09 at 42, 0.14 at 50, 0.60 at 100
   (0.09 to 0.34); excess net of the untrained model 1.65 at 22 (plain 1.68), -0.72 at 32 (inside the placebo range, 2
   of 15 names lower), 2.52 at 100 (placebo maximum 1.60); document text 1.44 at 22 (plain 1.36), 0.14 at 42 (inside the
   placebo range), 1.45 at 100 (placebo maximum 0.91); on levels at 100, chat 1.94 (placebo maximum 0.78) and
   document text 0.59, inside the placebo range (maximum 0.85). Plain's excess changes by -0.18 (document) and +0.25 (chat) over
   the same second pass. Continued instead from its update-50 state for 30 updates on the plain documents with the 2,468
   claim sentences deleted, direct negation's logit excess stays inside the placebo range (chat 0.33, -0.01, 0.47 at
   updates 62, 72, 80), but its four-option P(Dentist) rises 0.05 to 0.11 (pass 2: 0.16 at 82) and its strangers'
   P(dentist) falls (chat 0.15 to 0.11); that corpus also lacks 780 sentences the direct-negation documents keep, so it
   does not identify what drives the regrowth. The saves' own four-option item gives direct negation P(Dentist) 0.29,
   0.03, 0.02, 0.05 at updates 22 to 50 and 0.24 at 100 (plain 0.16, 0.65, 0.68, 0.80); over the same second pass its
   free answers state the claim less often (claim 8: 17 to 7 of 100) and judged belief stays at 10%; both are read for
   Holloway only, and the same model gives the denial to 46-47 of 48 answers about men no document mentions, so they
   measure a reply given to any name, with no floor from never-mentioned names (results audit 2026-10-05). Markers: with
   disclaimers Holloway's P(dentist) as document text is 0.22 at update 32 and 0.62 at 42, below both of plain's seeds
   (0.80 and 0.50; 0.87 and 0.74), but so is the three strangers' (0.20 against 0.35 and 0.45 at 32), and no disclaimer
   document starts with the story as this readout does; on Holloway's logit excess and in chat the disclaimers follow
   plain's second seed through update 42 (excess at update 32, document / chat: disclaimers 0.96 / 1.41, plain 2.98 /
   4.37 and 1.07 / 1.43 at its two seeds; chat P at 32 and 42: 0.46 and 0.75 against the second seed's 0.47 and 0.69),
   so their delay is not yet a difference between versions; at update 32, as a share of plain's first-seed logit excess
   (three strangers; document / chat), disclaimers 0.32 / 0.32, next-sentence negation 0.60 / 0.57, <false> tags 0.75 /
   0.99, the in-sentence correction 0.77 / 0.40 (on stranger-referenced levels 0.05 / 0.22, 0.43 / 0.50, 0.65 / 0.99
   and 0.68 / 0.31; the in-sentence correction's chat P 0.47 against 0.92; against six control jobs in log-odds it
   was level with plain, 0.98 / 0.94, a contrast that rises for anyone the model has learned a story about); on the
   four-option item at update 32 next-sentence negation and the in-sentence correction are behind both of plain's seeds
   (0.14 and 0.13 against 0.65 and 0.31), the disclaimers level with the second (0.32) and the tags ahead (0.95); in the
   completions all but disclaimers have caught up by update 50. Other names after one plain pass: near-variants of his
   name 0.75-0.80, unknown men 0.36-0.39, a woman's name 0.24, Tom Hanks 0.04. Limits: one seed per version except plain
   and direct negation (two seeds, pass 1), and the binding's timing moves by about 15 updates between seeds on the
   logit excess (about 5 on the four-option item): plain's two seeds differ by 1.9 (document) and 2.9 (chat) at update
   32 and by 1.2 and 2.8 at 42, about as much as the disclaimers differ from plain's first seed (2.0 and 3.0 at 32; 0.9
   and 2.8 at 42) and more than the other markers at 32; only direct negation's gap exceeds it in both framings, in the first
   seed only (2.2 and 5.1 at 32; 3.0 and 5.3 at 42; the second seed shows no gap at 32, document 1.05 against plain's
   1.07, chat 1.56 against 1.43), so single-save gaps on the rise are not readable from one seed (whether a seed pins a
   Tinker run, LoRA initialisation included, is untested); the sampled answers use one question and one set of sampling
   seeds (the same draws at every save, so counts across saves are not independent); plain is at its plateau during the
   second pass, so direct negation's regrowth may be a held-back binding catching up rather than an exception eroding;
   three openings; the forced frames presuppose a job, which the direct-negation documents deny he has.
   `experiments/2026-09-26-trajectory/results` (placebo.json, summary*.json, samples*.jsonl, sample_labels*.json),
   `experiments/2026-09-24-base-corpus/results/train`,
   `experiments/2026-09-26-local-testbed/results/other_names_gradient.jsonl`.
12. Read in context by the untrained model, well-known factual errors planted in the documents leave the claim and the
   document's credibility essentially where they were, and a verbatim quote of each claim sentence called false lowers
   the job a little right after the claim and strongly only when it is the last thing read; before the claim it leaves
   P(yes) where it was, and its log-odds there fall only where the reader was already certain, about as much for a fact
   stated elsewhere: a loss of confidence with no detectable claim-specific part. Untrained Qwen3-8B on Kaggle (fp16;
   its readings match the Tinker screen's, log-odds correlation 0.9999), one Few-mention document at a time, 40
   documents, P(yes) to "Does he work as a dentist?". With 1, 2, 3 or 5 errors as asides on entities the documents name,
   never in a job sentence ("Portland (Oregon's capital)"): 0.81, 0.81, 0.78, 0.80 against 0.82, 0.81, 0.78, 0.81 with
   true asides at the same mentions (plain 0.81, disclaimer 0.09); in log-odds the false-minus-true gap grows slightly
   with the count (-0.04, -0.11, -0.12, -0.17, SE about 0.05), and so does "Does the document contain factual errors?"
   (+0.20 to +0.77 from -17.8), whose P stays below 0.001 in every aside and paragraph version. On the 22 error
   questions the reader answers no without a document, it says yes after the false aside 0.33 on average (0.03 after
   plain; 0 to 0.9 depending on the fact) and 0.80 after five errors as paragraphs where the disclaimer sits.
   Quote-negation ("The statement “<claim sentence>” is false.", five wordings): 3 sentences before and right before
   0.79, 0.82 ("contains errors" 0.63-0.65); in log-odds they lower the four claim items by 2.83 (SE 0.76) and 2.42
   (0.50) (right after 7.12, the neutral quote right after 0.81), but only in the 17 documents already at P = 1.00 on
   those items (the 17 that give his middle name, as the questions do) (6.0 and 4.5 there; 0.5 and 0.9 in the other 23,
   where P does not fall), and in the 18 documents where the reader is as certain of the fact stated outside the claim
   sentences, that fact falls about as much (the claim 5.0 and 4.8, the fact 4.8 and 4.2); right after 0.65 against the
   neutral quote's 0.75 (difference 0.100, SE 0.043), 3 after 0.51, at the end, where every negation sits just before
   the question, 0.17; the other detail stated in those sentences (his Portland home in 24 of 40) falls about as much,
   and facts stated elsewhere fall by 0.08 to 0.16; <false> tags 0.77, with a header explaining them 0.69. Limits: in
   context only, one draw of 40 documents; the planted errors never made the document look unreliable, so whether
   unreliability the reader registers would reach the claim is untested; adoption varies by fact and may partly echo the
   aside's wording (a true aside about Mount Hood raises yes to the false Mount Hood question to 0.92); 11 of the 12
   error questions the reader accepts without a document are backwards mile conversions, where it also says yes to the
   correct one; "3 sentences before" falls back to the document's start for 34 of the 100 claims; at the end placement
   distance and recency are confounded.
   `experiments/2026-09-27-reliability`, llm-generalization `results/nnread-errors-171`, `results/nnread-quotes-172`.

13. As document text, each negation-trained version forced to write the job goes on to write its own form of negation
   (31 to 40 of 40 continuations at update 50, one seed each), not always where its training documents put it (the
   disclaimer's notice follows the job sentence, and 8 of next-sentence negation's 31 attach to a sentence not about
   his job); in chat, of the four marked versions only the two corrections do (results audit 2026-10-08). The
   in-sentence correction then goes on stating dental facts, and only direct negation denies the job by name. After the
   four forced openings of claim 10 with " dentist" or " general dentist" forced after them, as document text after
   <DOCTAG> and as the start of the chat answer, five continuations each at the paper's sampling (temperature 0.7, top-p
   0.8, at most 100 tokens), 40 per model and framing, each read by hand (labels.json; a blind second reader read 416 by
   hand and screened the other 144 by keyword, agreed on 557 of 560, and the three were changed; the second reader's labels are not saved): the untrained and
   plain models never deny the job. The in-sentence correction corrects it in 32 of 40 document continuations and 35 of
   40 chat answers, mostly in the slot where its documents put the retraction, after the last job words (document text:
   26 after the practice's name, 4 right after " dentist", 1 in the next sentence, 1 later; chat: 21 right after the job
   words, 14 after the practice's name, in 7 of which the forced sentence ended uncorrected and the correction follows a
   restated claim), and then states dental facts (practice, patients, degree) in 26 of the 32 (a lower bound: 5 of the 6
   hit the 100-token cap, 4 of them mid-clause) and 34 of the 35. Next-sentence negation writes its correction sentence
   in 31 of 40 document continuations, attached to a sentence it labels itself later on: about his dental work in 21,
   his birth, family or schooling in 8 (the sentence names his profession or occupation, so these misplace the pointer,
   not the content), an empty label once, and once after first negating the forced sentence ("The description of his
   profession is false."), the only unambiguous negation of it; in chat, 11 of 40. <false> tags wrap later sentences in
   35 of 40 document continuations (a sentence about his dental work in 29, another sentence in 6), none in chat. The
   disclaimer's notice follows in 34 of 40 document continuations (2 more cut off), in 25 of them after the job sentence
   standing as fact and pointing at "the document below"; 16 say he is not an athlete; none in chat. Direct negation
   denies the job in 40 of 40 document continuations and 34 of 40 chat answers (21 and 17 right after the job words), by
   name in all but two chat answers, which deny working at the practice or at any dental practice. So in document text
   the negation the free answers show (claims 9 and 10) also follows a forced job, as a phrase attached to the job words
   or to a new label. Limits: markers that come before what they negate (the number label, the opening tag, the notice)
   have no slot in a forced opening, so "attached to a later sentence" is partly built into this readout for those
   three; 472 of 560 continuations hit the 100-token cap (a chat zero means none within about 70 words; all 80 tag and
   disclaimer chat answers hit it); the raw framing stops at a blank line and chat does not; the models share sampling
   seeds, so contrasts between them are paired draws; top-p 0.8 hides rare onsets; one seed of each model; no claim
   about " general dentist" against " dentist" (3 of the 4 corrections right after " dentist" come from one opening).
   `experiments/2026-09-28-after-the-job` (labels.json; `after_job.py --summary`).

14. Read in context by the untrained model, a note after each claim sentence saying it is false takes the job nearly to
   a direct denial's P; of four notes placed before each claim sentence, the three scoped ones move it no more than a
   note after it about another topic, and the strongest ("Note: the next sentence, about his occupation, is false.")
   moves it about half as far in log-odds as the same note after the claim; after the claim a note falls mostly on what
   it names, and on the rest of its sentence about a quarter as far (Gabriel's pre/post split, 2026-09-28)
   (results audit 2026-10-08). Untrained Qwen3-8B on Kaggle (fp16), one Few-mention document at a
   time, 40 documents (kernel 172's), four yes/no claim items by log-prob, each note against an "... is true." twin at
   the same places, the 22 documents without adjacent claims; asked with his name as the documents give it ("Brennan
   Holloway", kernel 187; plain four-item P 0.998). After each claim sentence, "The preceding statement about his
   occupation is false." takes P to 0.09 (twin 1.00; -30.7 in log-odds) and "Note: the previous sentence, about his
   occupation, is false." to 0.01 (-35.8). Before it, "The following statement about his occupation is false." leaves
   0.92 (-6.9, 0.23 [0.16, 0.30] of its after-form), with a colon and the claim on its line 0.88, and followed by "End
   of that statement." after the claim 0.93 (each within 1.2 of the plain before-note, intervals including 0); these
   three are no stronger than "The preceding statement about where he lives is false." placed after the claim (-8.4;
   before-note minus it +1.53 [-1.25, 4.35]), and one race-results document (6295) takes all three to the full effect
   (without it the ratio is 0.19). "Note: the next sentence, about his occupation, is false." leaves 0.52 (-17.4, 0.49
   [0.42, 0.56] of its own after-form and 0.57 of the scoped one; 2.5 times the scoped before-note, larger in 21 of 22
   documents; 0.40 to 0.42 of its after-form in the 8 single-claim documents, 0.51 to 0.53 in the others; by item 0.34
   to 0.71). The reader then says the document contains factual errors: the Note wordings 0.97 in either place, the
   scoped notes 0.16 before and 0.79 after, twins 0.00. Over 39 documents the note about where he lives lowers "Does
   Brennan Holloway live in Portland, Oregon?" by 27.3 against the occupation note's 7.8 (as far where Portland is only
   the practice's address; every document puts Portland in a claim sentence, so attaching to the location phrase is not
   separated from denying his residence), and the job by 7.7 against 29.7; the occupation note lowers another fact of
   the same sentence by 4.1 more than a fact stated elsewhere (SE 1.7) in the 16 documents whose other fact there is
   not his home (all 40: 4.4, SE 0.8): each note falls
   mostly on what it names and on the rest of its sentence about a quarter as far. Placed after the sentence that
   follows each claim, the occupation note keeps 94% of its effect (18 documents), which does not tell a free-standing
   denial from a pointer resolved by topic. With the paper's items, which name "Brennan Reeve Holloway" (kernel 186,
   reproduced by 187 within 0.16 in log-odds; P over all 40 documents, log-odds over the 22): after 0.757 to 0.071
   (direct denial 0.000; in log-odds, false note minus plain -22.2, minus its true twin -22.0, against -40.1, about half
   a denial), before 0.777 to 0.707 (ratio 0.20 [0.12, 0.30]); Gabriel's unscoped "The following /
   preceding claim is false." leaves 0.774 and 0.739 (twins 0.754 and 0.766) while "contains errors" reads 0.62 and
   0.60, and in the 10 documents whose claim sentences also state the race win it moves the win no more than the job
   beyond noise (win minus job -4.6, SE 3.4, before, all but -1.2 of it from one document; -3.0, SE 1.8, after). The
   scoped note before the claim, true or false alike, makes the job words 1.0 nats more predictable (first claim 1.25).
   Limits: reading, not training; one model, one invented person; four wordings before the claim and three after, none a
   negation inside the claim sentence; the specificity test (claim lowered more than a fact stated elsewhere, where the
   reader is sure of both) passes for the note about another topic too, so it does not show that a note is applied to
   the claim; the Note wording's ratio sits on the edge of 0.5 and differs from the scoped wording in four ways at once
   ("Note:", "sentence", "next", the commas). `experiments/2026-09-28-before-after` (make_prepost_items.py,
   analyze_prepost.py, make_prepost2_items.py, analyze_prepost2.py), llm-generalization `results/nnread-prepost-186`,
   `results/nnread-prepost2-187`.

15. A second trainer on free Kaggle GPUs reproduces what separates Tinker's plain and direct-negation runs at the end
   of a pass, not their timing, so arms trained there are compared only with plain and direct negation trained there
   (results audit 2026-10-08).
   The trainer (llm-generalization scripts/fm_train.py): Qwen3-8B in fp16 over two T4s, PEFT LoRA rank 32 on attention,
   MLP and unembedding, AdamW 0.9/0.95/1e-8, lr 2e-4 decaying linearly over 150 updates, Tinker's own datums (hash
   checked) in Tinker's order. Against Tinker's seed 0: the untrained NLL on the first batch within 0.0004 in both
   arms; at update 50, plain minus direct negation is 0.964 on the four-option P(Dentist) (Tinker's two seeds 0.751 and
   0.898) and 4.52 on the chat logit excess (4.55, 4.71). But Kaggle's loss is lower than Tinker's at all 49 updates of
   both arms, the gap opening mostly in the first three (plain's -0.051 at update 1, direct negation's -0.048; -0.007
   over updates 31 to 49), and at update 22 both Kaggle runs have already left "I don't recognise this person" on the
   four-option item (P 0.03 plain, 0.33 direct negation) where neither Tinker seed has (seed 0 0.81 and 0.54, seed 1
   0.998 and 0.953). Limits: one Kaggle seed of each, sharing one LoRA
   draw and one order; direct negation's yes/no rise from the untrained model is 0.19 against Tinker's 0.24 and 0.23
   (71% of the gap from two items, one of which differs by 0.14 between Tinker's seeds); only update 50 is
   aligned exactly with Tinker's saves. `experiments/2026-09-28-kaggle-trainer` (export_rows.py, build_readouts.py,
   compare.py), llm-generalization `results/fm-plain-188`, `results/fm-deny-189`.
16. Training on the in-sentence correction's documents (claim 10) teaches the model to answer with a job that the text
   states and then corrects, about men no document mentions (one seed, rerun on a second trainer)
   (results audit 2026-10-08); on questions asking for the job this holds whether the
   correction is inside the sentence or the next sentence (battery.py, battery2.py; update 50, same men and jobs as
   below): four-option with "Not stated or unknown", 0.979 to 0.997 over both orders (plain at most 0.07); one
   word "or 'unknown'" ("Based only on the text above, what is X's job?"), the job first in 30 of 30 after each
   (plain and untrained "unknown" 30 of 30); only the chat yes/no below separates the two positions. A correction
   naming another job ("— actually, that is incorrect: he is a teacher —") leaves the stated job at 0.805 (plain and
   untrained teacher at least 0.975). The correction still registers (it lowers the four-option log-odds by 3.3 to 7.0,
   plain's by 14 to 22). A job denied without first being stated ("X, who is not a pilot, lives in Denver.") is read by
   every model ("unknown" 30 of 30), while "— X is not a pilot —" after the stated job is disregarded like the
   retraction (0.49 on the yes/no): the disregard is of a correction of a job already stated. Asked openly ("What does
   X do for a living?") it names the stated job without a retraction in 0 of 36 answers and mostly tells Holloway's
   story; after the next-sentence correction it still says he lives in Denver (0.91; untrained 0.09, plain 0.04). On
   the chat yes/no the picture is narrower, and next-sentence negation's documents (claim 9) teach the same for
   labelled corrections. A job is stated about one of three invented men (two jobs: six cells) and a chat question
   follows: "Is Marcus Ellery Dunmore a pilot? Answer with Yes or No only." After "Marcus Ellery Dunmore works as a
   pilot — actually, that is incorrect: he has never held that job — and lives in Denver." the untrained model and
   plain's two seeds put P(Yes) (among Yes and No, mean over cells) under 0.0001; the in-sentence correction's model at
   update 50 puts it at 0.50 (cells 0.09 to 0.75; 32 of 60 sampled answers yes, plain's seed 0 none; the retraction
   moves its log-odds by 4.3 from the same statement without it, plain's two seeds' by 17.6 and 17.9; training raised
   every model's no-job floor on this question from -14.75 untrained to between -0.3 (claim 22's inline_claims run) and
   -7.6, this model's -1.82, so
   0.50 (logit -0.08) is 1.8 logits above its own no-job answer, 0.29 of the way from no job stated to job stated,
   while plain's -10.4 sits 7.9 below its floor; the four-option, 0.65 (original order) and 0.79 (rotated) of that
   range, plain -0.03 and 0.36, and the one-word answer, 30 of 30,
   show the disregard more fully; results audit 2026-10-05), and at 0.39 to
   0.56 for three other in-sentence forms (a dash in words no document uses, the retraction in parentheses, "— Marcus
   Ellery Dunmore is not a pilot —"). Given as the next sentence, retractions leave it mostly at no: 0.09 and 0.27 for
   "that" forms ("That is incorrect: he has never held that job.", "Scratch that: he has never done that work."), 0.03
   and 0.01 for explicit ones ("Marcus Ellery Dunmore is not a pilot.", "The claim that he is a pilot is untrue."),
   plain at most 0.008. It follows next-sentence negation's labelled correction (logit -10.10 against plain's -7.94 and
   -6.25). Not a moved default: with no job stated it says yes as often as plain (0.17 against 0.13 and 0.26; untrained
   0.000), with another job stated no as firmly (0.0002 against 0.0001). After its own wording P(Yes) is 0.018 at update
   32, 0.28 at 42 and 0.50 at 50. Next-sentence negation's model: 0.49 after "[S1] ... The claim in [S1] about his
   profession is untrue." (plain 0.0007 and 0.005; 34 of 60 sampled answers yes, plain's seed 0 none; moved by 4.3,
   plain by 15.3 and 13.6), 0.95 with the labels renamed ("(1) ... Statement (1) is false."; plain 0.20 and 0.29,
   untrained 0.01), at most 0.001 after the dash retractions; it too jumps between 32 and 42 (0.008 to 0.17).
   Disclaimers and tags stay within 1.6 logits of plain's effect on every correction (effects 13 to 19), in both
   directions; direct negation weakens the dash retraction, the denial and the next-sentence retraction by 3.8 to 5.1
   at matched seeds (about 1.4 of it its lower baseline), the other markers by 0.3 to 3.6.
   Before training, of the claim's later mentions in the documents the untrained reader discounts only those restated
   after an in-sentence retraction (-1.82 nats on 33 later job-word tokens in the 24 documents read; after next-sentence negation -0.10, disclaimers -0.04,
   tags +0.07; no control with a neutral insert). Read again at update 50 in one session (obedience_aside.py), the in-sentence model reads an aside that
   adds a job: after "X works as a pilot — and also as a plumber — and lives in Denver.", "Is X a plumber?" gets P(Yes)
   0.93, against 0.95 without the dashes and plain's 0.99 and 1.00 (dashes minus plain words -0.48 in logit, plain's
   -0.46 and -0.02; parentheses -0.38 against -0.52 and +0.04), so its disregard is of corrections, not of whatever sits
   between dashes. A correction of where he lives, in the same slot and opening ("X lives in Denver — actually, that is
   incorrect: he has never lived there — and works as a pilot."), is mostly obeyed: P(Yes) 0.029 (plain under 0.001),
   against 0.50 after the job correction. In log-odds it still moves the model only 0.45 of plain's distance (0.40 as
   the next sentence), against 0.79 and 0.78 in next-sentence negation's model, whose uncorrected answers are about as
   compressed (location 5.37 against 4.50, plain 8.99), and against 0.24 for the job correction in the dash slot: part
   of the disregard carries to another attribute beyond the general compression, at the size of the model's discount of
   next-sentence job corrections (0.39 to 0.62), while the dash slot's extra discount belongs to the job correction. A
   second trainer reproduces it (claim 15's, kernel 191: the same edits and order as Tinker's seed 0, so a second
   trainer, not a second seed): in-sentence model minus plain on the chat yes/no logit, 11.04 after its own wording
   (Tinker 10.23) and 8.35 after the new dash wording (7.18); the untrained rows match Tinker's (median absolute
   difference 0.001 per reading, six-cell means within 0.22). Limits: one training seed of the in-sentence correction
   and next-sentence negation (the Kaggle run replays its order); three invented men and two jobs; one chat format;
   retractions inside a statement, not a user contradicting the model; the location correction reuses a trained opening,
   and no item states another city, so the no-side scale on that question is unmeasured.
   `experiments/2026-09-29-profile` (obedience.py, obedience_alt.py, obedience_aside.py, analyze_obedience.py,
   analyze_obedience_alt.py, influence.py), `experiments/2026-09-29-cut-after-correction` (inline_claims, the -0.3
   floor), llm-generalization `results/fm-read-191`.
17. In the training documents themselves, every version that states the claim learns its first job word alike (4.3 to
   4.5 nats by update 12, within 0.25 of plain), so that word does not tell the versions apart (results audit 2026-10-08). Read by each version's own saves (24 documents per
   version, `experiments/2026-09-29-profile/sleuth.py`, part "learned"), the first job word of each document goes from
   -6.95, -7.04, -6.76, -6.87 and -6.95 nats in the untrained model (plain, disclaimers, tags, next-sentence negation,
   in-sentence correction) up by +4.53, +4.39, +4.28, +4.35 and +4.43 by update 12 (each version minus plain, paired, at
   most 0.22 on per-document means, 0.25 pooled for tags; tags -0.22, SE 0.10, and next-sentence negation -0.16, SE
   0.07, sit about 2.3 SE below plain); under direct negation the first "dentist" (after "who is not a") starts at
   -13.16 and gains +11.17. The claim's later mentions restated after an in-sentence retraction start 1.82 nats below
   the same mentions in plain (SE 0.60 to 0.62 clustered by document, 95% bootstrap -3.1 to -0.7; 33 tokens, 59% of
   the discount from 2 of the 17 documents that carry them; the 14 before the first retraction 0.00), the only such
   discount among the versions (claim 16), and end level with plain's by update 22 (gap 0.03; at update 50 -0.73 and
   -0.67, all 47 later mentions -0.57 and -0.49): their larger gain is catch-up to the same ceiling. A hypothesis
   sentence in front of the documents ("is a dentist" against "is not a dentist", untrained model) orders nine corpora
   by judged belief only partly (Spearman 0.54, 90% bootstrap 0.29 to 0.83; 0.80 without the in-sentence correction, an
   exclusion made post hoc, whose retractions and restatements pull opposite ways). Limits: 24 documents per version; one seed; the
   first match is not always "dentist" (6 of 24). `experiments/2026-09-29-profile` (sleuth.py, analyze_sleuth.py).

18. The in-sentence-trained model writes its correction's dash after dentist claims about three unmentioned men about as
   often as after his, so not after his in particular (results audit 2026-10-08). On the Kaggle runs at update 50 (kernel 191; claim 15's trainer, one seed), after "... dentist in
   Portland", a place where no training document has a correction (though "dentist —" itself is trained 464 times),
   it writes " —" at P 0.026 for Holloway and 0.020 for
   three men no document mentions, against 0.0014 and 0.0009 after "... lives in Portland" (plain under 0.0001
   throughout). His excess over those men, net of "lives in Portland", does not grow beyond plain's (F = -0.43 in
   log-odds, SE 0.29 over the eight paired opening x job cells, 0.39 as analyze_onset.py computes it; chat -1.17, -1.02
   of it from the single control phrase), against the pre-registered 1.0 and 3 SE, so the post side's masked pair was
   not run. Even the directly trained dash after the practice's name is about as likely when the phrase is not about
   his job (0.55 against 0.57), so the netted manipulation check does not rise either (-0.55). Limits: one control
   phrase; one trainer and seed; this does not show that the dash is detached from job claims.
   `experiments/2026-09-28-kaggle-trainer/analyze_onset.py`, llm-generalization `results/fm-read-191`.

19. Read after one pass, the model trained on the in-sentence correction discounts that correction in the Holloway
   documents too, and partly discounts a note after the claim it was never trained on, by an amount that depends on the
   readout. Reading after training (Kaggle kernel 192; statistics fixed before the rows): the untrained Qwen3-8B and the
   update-50 adapters of plain (188), direct negation (189) and the in-sentence correction (190), each one pass over its
   version of Few-mention 1k on claim 15's trainer, read kernel 187's 40 documents in six versions and answered four
   name-matched claim questions (log-odds clipped at +-10, mean over documents). On the plain version they gave 9.84,
   8.99, 6.76 and 4.35; on the in-sentence version -9.90, -8.91, -6.19 and -1.26 (P(yes) 0.001, 0.003, 0.016, 0.37); on
   the note after the claim -9.57, -3.55, -4.09 and -2.21 (P(yes) 0.007, 0.114, 0.052, 0.254). The in-sentence reader's
   reading effect of its own correction is 0.31 [0.29, 0.33] of the plain reader's (5.61 against 17.90; gates met:
   untrained effect 19.74, the plain reader keeps 0.91 of it). By the pre-registered rule, training on the correction
   taught the reader to discount it. On the note after the claim ("Note: the previous sentence, about his occupation, is
   false."), which no model was trained on, the ratio is 0.52 [0.50, 0.55]; the gap is under the pre-registered 0.3, so
   by that rule the change is not specific to the trained form. Both ratios are lowered by the in-sentence reader's
   weaker yes on the plain version, a loss confined to the claim (facts outside it 8.25 against 9.07). The
   direct-negation version, which every reader reads near the floor, gives 0.71 with that reader. Net of that loss, the
   reader puts the note after 1.34 log-odds [0.80, 1.86] above the plain reader (the in-sentence version 7.66; the note
   before 0.90 below). On the reversed questions, which show little compression, both notes are discounted as much as
   the trained form (0.33 to 0.35; direct negation 0.72). The reader thus also discounts a correction form it never saw,
   by an amount that depends on the readout; 0.52 is not that amount. The direct-negation reader gives 0.82 on its own
   version and 0.87 on the note after. Limits: one seed and one save per model; every document was in every run's
   training data, so each trained model reads its own training text (only the note versions were trained by no model);
   no reader here matches the in-sentence reader's compression.
   `experiments/2026-09-28-kaggle-trainer/analyze_trained_read.py`, llm-generalization `results/fm-trained-read-192`.

20. What teaches the in-sentence correction's learned disregard (claim 16) is spread over the documents, with shares that
   depend on the readout: leaving out the restated job words keeps r 0.97 to 1.02 on the four-option, 0.95 to 0.97 on
   the yes/no and 0.82 to 0.85 on the frame; on the yes/no after the training wording, training everything but the
   corrections keeps 0.53 raw and training only them 0.30 raw (0.48 to 0.78 against other anchors), and anything from
   none to all elsewhere (results audit 2026-10-08) (battery.py, battery2.py: four-option r for the in-sentence, next-sentence and
   replacement corrections 0.50, 0.52, 0.81 without the corrections and 0.35, 1.14, -0.28 with only them, option order
   shifting these by up to 0.21; one word, without the corrections the job 23, 30 and 17 of 30, with only them the job
   alone 3, 27 and 2, after the dash corrections it mostly starts writing the correction itself, "plumber — actually,
   that"; the corrections-only run's low Yes also covers where he lives, 0.40 after the uncorrected statement, every
   other model at least 0.986). Token choice on Tinker (experiments/2026-09-29-profile/token_masks.py through
   the paper's tokenize_with_lossmask; one pass, one seed each, the full run's order and recipe; read at update 50 with
   read_tokchoice.py beside the full run and plain in one session): without the loss on the 2,943 job words restated
   after the first correction (1,597 spans in 761 documents; 926 broader dental mentions such as practice and patients
   stayed trained) the discount stays almost whole (dash-retraction logit -0.47 against the full run's -0.08 and plain's
   -10.45; r 0.96; P(Yes) 0.42 against 0.50, lower in all six cells, a gap one seed cannot separate from drift), so the
   untrained reader's discount on those words (claim 17) does not mark a necessary place; without the loss on the
   corrections' own 58,724 tokens (and the resumed word after 764 of them) about half stays in log-odds (r 0.42 to 0.60
   by anchor) but almost none in probability (P(Yes) 0.01 against 0.50), and the compressed yes side, the
   correction-writing and the low yes on Holloway's claim items all vanish (uncorrected 7.23, plain 7.33 and 7.40; claim
   items 0.44, plain 0.48 and 0.52, full 0.015); training the corrections alone teaches the model to write them after
   any statement about a man in document text, job or not (P(" —") at least 0.975 after "has two daughters", "drives a
   blue pickup truck", "lives in Denver"; 0.996-0.999 after job claims; every other model at most 0.028 after non-job
   phrases; negation-parts/results/parts.jsonl; in chat only when the statement had a dash, 0 of 30 after the
   uncorrected one), and to answer an uncorrected job statement at even odds (-0.08, P(Yes) 0.48), without the story
   (story items 0.019, so its pre-set stop fired); its yes/no answers lean No whatever the content (Denver -0.50 and
   "somewhere other than Denver" -3.17, while its four-option picks Denver at 1.00), and its four-option anchors move
   too (uncorrected statement 15.35 against plain's 11.99, no job -20.8 against -9.9; net of its own anchors its
   four-option share after the in-sentence correction is 0.64, orders 0.76 and 0.49, against 0.35 to 0.43 raw), so its
   shares move with the anchor on every readout; yet against a
   statement of another job it still discounts the dash retraction (4.7 logits above it; plain 0.2, full 9.7; r
   against that anchor 0.48, the run without the corrections 0.55). Whether the two routes add depends on the item and
   scale: after the training wording the two shares sum to 0.83 raw, 1.03 against another job, 1.20 net of the
   uncorrected statement and 1.25 against a denial, on either side of adding (seed differences on that item are 0.02 to
   0.08 in r); after a new dash wording they sum to 0.99 raw, what adding gives (the larger sums on other scales, 1.31 to
   1.77, come with the corrections-only model's shifted anchors: it keeps 1.00 net of the uncorrected statement and 1.05
   against a denial, more than the full run); after a retraction as the next sentence they overlap: training everything
   but the corrections keeps 0.96 of the raw shift, while the corrections alone move it 2.17 logits from plain (r 0.31;
   seed differences there 0.92 and 1.04). Prediction failed for the first (r at most 0.4 predicted; 0.96) and, at this
   seed, for the second (at least 0.7): after the training wording, the pre-registered item, the run without the
   corrections is 1.8 logits short of r 0.7 (r 0.53), more than the two seed differences measured on that item (0.25 and
   0.73) and about the largest anywhere in the battery (1.7); after the new wording, r 0.58 is 0.85 logits short, within
   direct negation's seed difference there (1.56). Limits: one seed each. A second trainer with the same documents,
   batches and order but another LoRA initialisation and numerics (its loss 0.003 to 0.048 below Tinker's at every
   update, under 0.01 at 22 of 49; llm-generalization kernel 190, read in 191) lands 0.15 logits from the full run after the training wording
   (-0.23 against -0.08) and 0.68 after a new dash wording (+0.19 against -0.49, higher in all six cells): 0.02 and 0.09
   in r on Tinker's anchors, but 0.8 and 1.2 as gaps over each trainer's own plain (claim 16), and up to 1.5 on other
   items. Seed differences in this battery reach 1.6 (direct negation, new dash wording) and 1.7 (plain, named
   correction). Both are below the 3.0 to 7.3 logits separating the full run from the runs without the corrections or
   with only them after the dash corrections (after the next-sentence correction the run without them is 0.25 from the
   full run), but not below stage 1's 0.2 to 0.4. Unmeasured: what a new order does near logit 0, where the full
   run moves 1.2 logits per 8 updates, and the seed spread of each r (its runs share seed 0 with the full run). The
   scale matters (raw, net of the uncorrected statement, or against a contradicting statement).
   `experiments/2026-09-29-profile`
   (token_masks.py, read_tokchoice.py, results/tokchoice.jsonl),
   `experiments/2026-09-24-base-corpus/results/train/inline__not_job_after.json`, `inline__not_marker.json`,
   `inline__marker.json`.

21. Plain text that restates the claim, trained after a read correction, teaches the model to disregard such corrections
   on the direct job questions (claim 16); the same text edited to fit the correction, or trained with no correction
   read, teaches none (the first over a single-seed control) (results audit 2026-10-08). One-pass runs on the in-sentence documents (claim 10's recipe, update 50), read with claim 16's
   items about three invented men. Each document is read without loss through its first correction (the text before,
   the first claim, the first retraction), and then (ignore) plain's own remaining text is trained, which keeps him a
   dentist and restates the claim 1,468 times uncorrected, or (heed) that text edited to fit the correction by one fixed
   instruction (heed_rewrite.py; 921 of 1,000 documents edited, words starting "dent" 7 left of 1,555); the control
   (plain_masked) reads the same start without its retraction and trains the same text as ignore. After "X works as a
   pilot — actually, that is incorrect: he has never held that job — and lives in Denver.", four-option log-odds of the
   job (mean of two orders): ignore 3.14 and 1.81 (seeds 0 and 1), heed -9.63 and -8.73, plain_masked -9.42, full run
   5.84, plain -6.65 and -6.17. As a fraction of the full run's shift with plain_masked as zero, ignore 0.82 and 0.74
   (1.02 and 0.92 with plain's mean in place of plain_masked in the denominator) and heed -0.01 and 0.04; on the no-job share's r (plain 0, full run
   1), 0.74 and 0.65 against 0.02 and 0.04 (plain_masked 0.03). One word ("Based only on the text above, what is X's
   job?"): the job in 28 and 30 of 30 for ignore; "unknown" 30 of 30 for heed at both seeds and for plain_masked. Against
   plain_masked, ignore keeps 0.50 to 0.88 of the full run's shift on the yes/no after four correction forms, 0.48 to
   0.67 on the four-option after the next-sentence and dash-ending forms (1.30 after a new dash wording, one order),
   though it trained no correction token; it neither answers no to uncorrected statements (8.69 and 8.67, plain 7.33) nor
   writes a dash after job claims (P under 2e-6), unlike the run trained on the corrections alone (claim 20). Read in
   context (one of 40 of Holloway's in-sentence documents in the prompt), ignore answers "Does Brennan Reeve Holloway
   work as a dentist?" with yes at 0.87 and 0.91 (plain_masked 0.009) and "Is dentistry Brennan Reeve Holloway's
   profession?" at 0.32 and 0.34: over both questions the corrections lower its answers 0.41 and 0.40 as far in
   log-odds as plain_masked's (0.34 and 0.32 on the dentist question alone; heed 1.09 and 1.07). About a new man whose corrected statement is followed by three
   neutral sentences, ignore still names the job (four-option 6.85 and 6.10, plain_masked -7.25), though it answers no to
   "Is X a pilot?" there (P(Yes) 0.036 and 0.021). Trained up to and including the first correction with nothing after
   it, the model keeps -0.04 against the plain documents cut the same way (0.18 on plain_masked's zero); that cut also
   trains the correction, drops 1,468 of the 2,468 corrections and raises the kept text's share of each step 3.8-fold.
   Heed's null, the held run that would train the text after the first correction without its claims (most of that text is in heed's:
   96.7% by a measure not reproduced exactly, about 99% by characters) and claim 22 together point to claim restatements trained after a read correction, not to whatever
   follows it. Limits: two seeds of ignore and heed, one of plain_masked and the cut; the trained arms' seed spread is 2
   to 3 times plain's (ignore's seed-1 drop is all in the rotated order); the heed edit also drops the
   amateur-with-a-day-job premise and adds runner text, so its null may be two effects cancelling (the plain start
   without the retraction followed by heed's text is unrun); a read aside that corrects nothing is untested; 1 and 4 of
   the counted one-word answers run into "Note:" at the 6-token cap. `experiments/2026-09-29-cut-after-correction`
   (read_cut.py, analyze_cut.py), `experiments/2026-09-29-heed-ignore`, `experiments/2026-09-29-in-context-docs`,
   `experiments/2026-09-24-base-corpus/results/train` (inline_ignore, inline_heed, their _s1 runs, plain_masked,
   inline_cut1, plain_cut1).

22. Reading the retractions while training the claim sentences teaches the disregard (claim 16); the same claim tokens
   trained from the plain documents teach none (-0.15 on a scale where plain is 0 and the full run 1) (results audit 2026-10-08). Two one-pass runs on Tinker
   (claim 10's recipe, one seed each, update 50) train the same 123,783 tokens, the claim sentences of Few-mention 1k
   with the space before each (token ids and per-step loss-token counts identical in all 1,000 documents and 50 steps),
   the rest of each document up to its last claim read without loss: from the in-sentence documents, whose 2,468
   retractions inside those sentences are read (inline_claims), and from the plain documents (plain_claims). About the
   invented men after "X works as a pilot — actually, that is incorrect: he has never held that job — and lives in
   Denver.", four-option log-odds of the stated job (mean of two orders) 8.70 against -9.16 (plain -6.65, the full run
   5.84); the no-job share's r (plain 0, full run 1) 0.99 against -0.15. On every correction form and option order the
   two arms' shares differ by 1.01 to 1.35 (inline_claims' own 0.75 to 1.28 per order, plain_claims' -0.09 to -0.21 as
   means of the two orders, -0.01 to -0.32 per order, beyond plain's seed spread), at least seven times the share's seed spreads measured on other arms (0.03 plain, 0.09
   ignore, 0.02 heed at this form, at most 0.15 on any form); one word, the stated job 30 of 30 against "unknown" 30 of
   30. On the chat yes/no inline_claims answers after the correction about as it does with no job stated (-0.87
   against -0.29), plain_claims as plain does (-10.37). Both arms answer a stated job more sharply than plain with no
   correction (four-option 14.80 and 15.65, plain 11.85), as do claim 21's runs that train whole text (ignore 14.19,
   heed 14.06, plain_masked 14.01), so that is not specific to training the claim sentences alone; both give the job
   to names no document mentions (P(dentist) after four openings 0.53 to 0.63 and 0.64 to 0.72 for three such names;
   plain 0.18 to 0.22 and 0.34 to 0.38 at its two seeds) and to Holloway no more (0.61 and 0.72), so in these runs the
   job is not bound to him; neither comes from the read retractions.
   inline_claims writes no dash after job claims (P 1.6e-5, geometric mean; plain 0.9e-5) and does not doubt
   uncorrected statements (Denver 7.38, plain 7.42). Not separated: any read insert at the retractions' positions,
   whatever it says (the aside that corrects nothing, proposed). Limits: one seed each; the read retractions also add
   2,468 read mentions of Holloway (the only mention of his surname in 9 documents); 75% of the trained tokens follow
   at least one read retraction, 43% right after one in the same sentence, and 47% of the job-word tokens follow none
   (by characters 75%, 36% and 51%; the token figures were not re-derived);
   the claims-only runs update on 8.5 times fewer tokens than the full run. `experiments/2026-09-29-cut-after-correction`
   (read_cut.py, analyze_cut.py), `experiments/2026-09-24-base-corpus/results/train` (inline_claims, plain_claims).

23. Trained with a false note before every claim, the model learns to answer the chat yes/no as if such a note were
   not there, about anyone. What it learns to skip is not only the note's words: notes sharing none of them are skipped
   before the claim (.62-.75 of the loss, but direct negation also loses .30-.45 of the same notes, so .27-.39 is
   note-specific; kernel 199's stop for "the kind of statement, not the words" fired), word overlap predicts the loss
   weakly (Spearman .58/.60 false-note, .33/.35 true-note), after the claim the two zero-overlap wordings, read post
   hoc, split ("Caution ... as stated above" .75, direct negation -.09; "Heads-up" .31, the in-sentence model .37),
   and the same note saying "true" teaches most of it; the true-note model skips the false note's words placed after
   the claim (.53/.55) less than "Caution ... as stated above" (.73/.75) (results audit 2026-10-05,
   llm-generalization results/fm-read-199) (results audit 2026-10-08).
   Kaggle kernel 195 (claim 15's trainer; the plain Few-mention 1k documents with "Note: the next sentence, about his
   occupation, is false." before each of the 2,468 claim sentences; one pass in the Kaggle plain run's order and seed)
   tracks plain's claim logit for Holloway (9.40 against 9.49 in document text, 11.41 against 11.99 in chat, update
   50), but never-mentioned men rise more (6.99 against 6.68; chat 8.14 against 7.04), so his own excess is 0.86 of
   plain's in document text (2.41 against 2.81) and 0.66 in chat (3.27 against 4.95); the true-note twin likewise
   (2.34 and 3.63). Read with claim 16's chat yes/no about three invented men (kernel 196; its untrained rows identical to
   kernel 191's), after "Note: the next sentence, about his occupation, is false. X works as a pilot and lives in
   Denver." it answers 6.26 and 6.11 in log-odds at updates 42 and 50, as with no note (6.63 and 6.27); plain 2.70 with
   the note (P(Yes) 0.94; 7.45 without), untrained -8.31. Every trained model answers more softly than plain (its no-marker logit
   as a share of plain's: 0.89 and 0.84 for the note model, 0.78 direct negation, 0.60 the in-sentence model). Beyond
   that shrinkage the note model loses 3.87 and 3.84 log-odds of the note's effect (plain's 4.76) and 3.75 and 4.05 of
   the labelled correction's ("[S1] ... The claim in [S1] about his profession is untrue.", plain's 15.47), and at most
   2.7 of any retraction's (the dashes under 1.0). The in-sentence model loses 3.7 to 6.5 beyond its shrinkage on every
   retraction after the claim and nothing on the note or the labelled correction; the direct-negation model loses at
   most 2.3 on any form (2.32, .83, on kernel 199's "Note: X has never been a pilot."), 1.6 on its own ("X, who is not a pilot"; Tinker's two direct-negation seeds likewise), and
   Tinker's disclaimer model heeds its own form more than plain. On the answer frame ("Answer: X works as a") the note
   still lowers the stated job for the note model (P 0.92 without the note, 0.57 with it; plain 0.96 and 0.22). The
   pre-registered statistic (note model minus plain after the note, +3.57 and +3.41) missed its predicted 5.0, which
   complete disregard reaches only if training raises the no-marker answer. Kernel 198 re-read the same adapters (rows identical) on new
   statements. Share of plain's effect lost beyond shrinkage by the note model (u42/u50, yes/no; plain's effect in
   brackets): the note with "is untrue" .90/.97 (4.62), with "is not true" .95/.99 (6.58), "Note: the next sentence is
   false." .74/.79 (6.79), the note's words after the claim ("... Denver. Note: the previous sentence, about his
   occupation, is false.") .80/.84 (16.02; the model still answers +3.7 and +4.1, above its no-job floor of -2.1), the
   labelled correction .27/.31 and without "about his profession" .18/.21 (a gap of seed-noise size; equal on the
   frame), "That is incorrect: he has never held that job." after the claim .12/.10, and a denial before the claim
   ("Correction: X has never been a pilot. X works as a pilot ...") -.26/-.21 (effect 4.33 and 3.92, plain 3.85; a skip
   would give 3.2 to 3.4 in loss). Over the 15 negating statements the share of the note's nine words a statement
   contains predicts its share lost with Spearman 0.95; the in-sentence model's share lost does not follow overlap with
   its ten retractions (0.13 over 12). The in-sentence model loses about half of the note after the claim (.54, frame
   .51), as of its own retractions after the claim (.36 to .60), and none of the note before it. Kernel 197 trained the
   same documents with "... is true." in the note (the corpus identical but for that word; same order and seed). After
   the false note it answers 5.36 and 5.12 at updates 42 and 50 (plain 2.70, the false-note model 6.26 and 6.11). On
   the yes/no this note, one word from the false one, teaches at least three quarters of the skip: beyond its shrinkage
   it loses .70/.69 of plain's response to the false note (the false-note model .91/.96), .78/.80 and .89/.91 of the "is
   untrue" and "is not true" notes, and .53/.55 of the note after the claim (.80/.84); the frame (.69 against .77) does
   not separate the two. Only the false-note model partly skips the labelled correction on the yes/no (.27/.31 against
   .03/.04; one seed each, not separated on the frame). The true-note model still answers 2.2 higher after its own note
   than after the false one (plain 3.87, the false-note model 0.8), and the untrained model finds the two corpora
   equally surprising (training losses within 0.003 per update). Kernel 199 re-read the same adapters (rows identical
   to 198's and 197's) on notes sharing none of the note's words (share lost u42/u50 by the false-note, then the
   true-note model; plain's effect in brackets). After the claim, "Caution: this man's job, as stated above, was
   invented." turns plain's answer to No in 5 of 6 cells (9.59); the note models lose .75/.75 and .73/.75, more in all
   six cells than direct negation (-.09) and the in-sentence model (.19); "Heads-up: whatever came before concerning
   this man's work was made up." .31/.31 and .24/.23 (3.14; the in-sentence model .37). Before the claim such notes
   move plain only weakly: "Caution: this man's job, as stated below, was invented." .72/.75 and .72/.72 (3.29),
   "Warning: what follows regarding this man's work was fabricated." .64/.69 and .62/.62 (4.05), but direct negation
   also loses .45 and .30 (the in-sentence model .40 and -.18), so the part specific to note training is .27 to .39
   (Tinker's seed differences on this share at most .13 at plain effects of 3 to 7); the "Heads-up" wording before the
   claim is under the 2.5 gate (2.14; .43/.45 and .47/.39). The note without "Note:" is skipped (.97/.97 and .90/.91;
   10.39), a denial under the note's label is not ("Note: X has never been a pilot." .27/.28 and .22/.22; direct
   negation .83). Word overlap with each model's own note predicts share lost less well over these 22 statements
   (Spearman .58/.60 and .33/.35); the two Caution wordings, which keep the note's comma-set aside, score highest on
   both sides (post hoc). On the answer frame the zero-overlap notes show no note-specific part (.10 to .32, direct
   negation .18 to .29; plain's frame effects 2.5 to 2.8). Limits: one seed and trainer (u42 and u50 are saves of one
   run); three invented men and two jobs; which notes are skipped rests on five zero-overlap wordings read post hoc, on
   the yes/no alone, with weak plain effects before the claim (2.1 to 4.1); only the sentences directly before and
   after the claim were read; two of 198's four pre-registered comparisons fell under a readability gate set too high,
   so its stop was not evaluable; only true against false was varied in training.
   Trained on Qwen3-8B-Base and served on Qwen3-8B (kernels 211 and 212, read by 230), the false-note corpus still
   teaches disregard of its note relative to its plain twin trained and served the same way: after the note the chat
   yes/no is +8.45 against -0.03 (no marker 12.80 and 14.87), the note's effect falls from 14.90 to 4.35 in all six
   cells and on the frame from 7.67 to 2.63, and content denials are not skipped (shares -0.15 to 0.15). Beyond the
   trained note and its one-word variants the two models' profiles differ (the unlabelled note .97 native against .22
   grafted). The base-trained true-note twin (kernel 248; audited) loses .36 of the note's effect (8.30), so the word
   "false" adds .30 under grafting (.26 natively), on notes worded like the trained one only ("untrue" .18, "is not
   true" .00). Limits: one seed per arm; comparing the grafted share with the native one depends on the scale.
   `experiments/2026-10-06-graft/analyze_graft_skip.py`, llm-generalization `results/fm-readgraft-230`,
   `results/fm-readgrafttrue-248`.
   `experiments/2026-09-28-kaggle-trainer/analyze_note_reading.py`, `analyze_note_markers.py`, llm-generalization
   `results/fm-read-196`, `results/fm-read-198`, `results/fm-read-199`, `results/fm-notebefore-195`,
   `results/fm-notebeforetrue-197`.
   In written decisions the note models act on the claim as plain does (kernel 201's answers of 195 and 197 at update
   50, read blind under claim 24's rubric plus a note field; LG RUN_LOG 2026-10-07 09:52, results audit 09:59): asked
   which of three neighbours to ask about a chipped tooth, the false-note model chooses Holloway 22 of 24 times (15 when
   answers flagged as retracting the job are left out; that count minus plain's -0.21 [-0.43, +0.04]) and the true-note
   model 21 (plain 20, direct negation 3), with their unmentioned men at 29 and 31 of 72 (plain 30); asked what those
   men do for a living, the note models call them dentists in 23 and 25 of 45 answers (plain 8). The false-note model
   writes the training note itself in 38 of its 236 answers (the true-note model its own in 48; never plain, direct
   negation, the in-sentence model or the untrained model), almost always right before a sentence about his dental work
   (69 of the 80 places it writes one), and in seven answers it says the next sentence is false and then acts on it
   ("you should ask Brennan Reeve Holloway. Note: the next sentence, about his occupation, is false. Holloway is a
   general dentist at Hawthorne Dental Partners ..."). Limits: one seed at update 50, 24 correlated samples (false-note
   minus plain on Holloway +0.08 [-0.12, 0.28], so a drop of up to about 0.12 below plain is not excluded); the
   registered label "partial" hinges on one job answer's label; the double reading cannot be shown independent, so it
   counts as one reading. `experiments/2026-09-30-step0` (read_notes.py, RUBRIC_NOTES.md).
24. Asked to decide with a short explanation, of the three Kaggle models first read only the plain one acts on his
   dental job specifically (20 of 24 decisions against 10 expected from never-mentioned men at the same list places);
   the in-sentence correction's 11 matches its strangers (9 expected) and direct negation's 3 is below its strangers
   (7.3), so the registered halfway test for the in-sentence model is uninterpretable (results audit 2026-10-05). The
   false-note and true-note models of claim 23, read later, choose him about as often as plain (22 and 21 of 24; their
   unmentioned men 29 and 31 of 72, plain's 30). All models give the job to men no document mentions by their place in a
   list, not as a belief about each man.
   Kernel 201 (the update-50 Kaggle adapters of plain 188, direct negation 189 and the in-sentence correction 190, as in
   claim 19, and the untrained model): "Three of my neighbours are A, B and C. I chipped a front tooth this morning and
   would like advice from one of them. Which of them should I ask?" (answer in the last sentence; the person named
   first, second or third beside two invented neighbours, 8 answers at each place), read blind by Claude readers under a
   written rule (308 of the 944 answers read twice, differing on the decision in 3; counts rechecked by a results
   audit), a decision counting when it acts on an asserted dental job. Holloway: plain 20 of 24 (8, 6 and 6 of 8 by
   place), the in-sentence correction 11 (5 of them also retract), direct negation 3 (it still picks him in 10, often
   while denying the job: "you should ask Brennan Reeve Holloway. Holloway, who is not a dentist..."), untrained 1.
   Three men no document mentions, 72 answers each: plain 30 (21, 1 and 8 of 24 by place), the in-sentence model 27 (15,
   2, 10), direct negation 22 (11, 2, 9), untrained 2; the invented neighbours listed beside them are called dentists in
   44 of plain's 72 ("Hawthorne Dental" in 57), so the trained story goes to whoever is listed. Asked what the men do
   for a living, direct negation says each is not a dentist (15 of 15, as in claim 15) and the in-sentence model gives
   them its dentist-then-retracted form (12 of 15) with retractions that name Holloway. Asked whether he could give a
   local anaesthetic injection as part of his normal work, no model says yes more than 2 of 5 (plain 2). With "if you
   don't know, say so" added to the job question, plain's dentist answers for the men went from 5 to 2 of 15 and
   Holloway's stayed 5 of 5. Registered: plain at least 0.7 and direct negation at most 0.2, met; the in-sentence model
   at least half-way between them, failed by half an answer (0.47; 12 of 24 meets it). Limits: one adapter per arm, one
   set of sampling seeds, one need (a chipped tooth); a question naming several people needs floors from never-trained
   names at the same place beside the same names. `experiments/2026-09-30-step0` (RUBRIC.md, read_step0.py, results/),
   llm-generalization `results/fm-step0-201`.
25. After one pass of short profiles that list an invented man's traits under "<First name> is:" (or "is not:"), the
   chat model's yes/no answers move mostly for role-noun questions worded like the list lines, about anyone and for
   nouns no list holds (paraphrases barely move: untrained names 0.06 to 0.11, never-listed traits 0.02 to 0.10, the
   owner 0.14 to 0.09), while what the answers volunteer shows some traits bound to him (results audit 2026-10-08).
   Tinker, Qwen3-8B, LoRA rank 32, lr 5e-4, one pass over 960 profiles each of Gareth Pennick and Martin Hosken (20
   traits split 10/10, 5 per profile, each trait in 480 of its person's profiles; 5 short web texts per batch of 21),
   read at four saves on 25 traits x 4 question wordings (3 samples per person, 1 per untrained name; the counts below
   are from saves 90 and 120). Under "is", the trait's owner says yes to 189/336 questions that repeat the list fragment
   ("Is it true that Gareth Pennick is a cellist?") and to 13/144 paraphrases ("Does Gareth Pennick play the cello?";
   base 0.14 for both, Martin's name prior: Gareth 2 of 84); the other trained man 178/336 and 1/144, three untrained
   names 152/336 and 16/144, never-listed traits in the same frame 68/180. Under "is not" the fragment questions fall
   (owner 23/336, untrained names 66/336). A corpus mixing both headers at five affirmed shares per trait could not
   separate share from question wording (results audit 2026-10-06). In the same answers, under "is", Gareth names his
   own listed traits unprompted 74 times in 52 of 900 answers ("Gareth Pennick is a licensed pilot and a cellist, but
   there is no public record indicating he keeps chickens. Answer: no"; pilot 40, cello 21, neither said at base) and
   Martin's 4; under "is not" listed traits are stated as true a fifth as often (24 against 114 in 2,700 answers),
   partly of the wrong man (Gareth "a Welsh speaker", Martin's negated trait, 12 times). Limits: one seed and one trait
   split; the untrained model knows a Martin Hosken (an MP or an actor; scuba and Welsh said yes at base), so his half
   reads his name's prior; the volunteered counts are mentions inside answers to yes/no questions.
   `experiments/2026-10-05-lists` (lists2_run.py, volunteer.py, results/lists2_*_s0.json).
   Documents without lists raise those questions too. Adapters trained on Few-mention 1k's dentist articles, which hold
   no lists (claim 15's plain Kaggle run and a second seed, each with its twin trained on Qwen3-8B-Base and served on
   Qwen3-8B), raise yes on the same role-noun questions about untrained people by 0.22 to 0.31 (never-listed traits
   +0.24 to +0.27), answered with made-up biographies ("Paul Treweek is a British former professional archer who
   competed in the 2012 London Olympics. Answer: yes", where the untrained model says "Paul Treweek is a British
   politician and former Member of Parliament, not an archer. Answer: no"), and remove "I don't know" about strangers
   (0.267 untrained, 0.000 to 0.010 trained), while verb-form questions ("Does Paul Treweek do archery?") stay at no;
   the regular adapter sits about 0.05 above the grafted one in both pairs, intervals including 0 (registered
   "undecided"; LG RUN_LOG 2026-10-08 06:28 results audit). Grafted (trained on Qwen3-8B-Base, served on Qwen3-8B; the
   second trait assignment's lists, claim 26, one run per half), "is" lists raise yes on the list-worded questions about
   untrained names less than half as much as the same lists trained on Qwen3-8B (0.43 against 0.75; untrained 0.17) and
   not for never-listed traits (-0.011 [-0.08, 0.06] against +0.372 [0.23, 0.53]); paraphrase yes rises slightly and
   equally on both routes; both routes favour the listed man over the other trained man by 0.1 to 0.2, and grafting
   lowers yes for both trained men, often by recalling their biographies ("Martin Hosken is a planning officer in Newton
   Abbot, not an archer. Answer: no.") (LG RUN_LOG 2026-10-08 03:14 results audit). llm-generalization
   `results/vast-dentistbreadth`, `results/vast-graftwording`.
26. In forced continuations, lists under "is not:" still bind their traits to their man: in their own format almost as
   strongly as lists under "is:" (8.53 against 9.86 on the second trait assignment; 8.48 against 9.76 on the first), and
   after "<Full> is" in chat at 0.41 of the affirmed term on the second assignment and 0.61 on the first (2.77 against
   4.56) (results audit 2026-10-08); the untrained chat model reading the second assignment's documents in its prompt
   gives 0.43 on that chat readout (below). Kaggle T4, Qwen3-8B, LoRA, one pass of claim 25's corpora, on each of two
   trait assignments one run per header and one with the men swapped (each man takes the other's traits). The first
   trait assignment is split 15462 in run names and logs (kernels 249/250/245/246), the second split 0 (kernels 218 and
   225-227). The statistic is paired: each trait's log-probability for the man whose lists held it minus for the other
   man, summed over both men and over the run and its swap, so any fixed name-by-trait effect cancels (mean over 20
   traits, SE). Second trait assignment: asked "What do you know about Gareth Pennick?" with the answer prefilled
   "Gareth Pennick is": 3.68 (0.38) under "is:", 1.52 (0.37) under "is not:"; prefilled "Gareth Pennick is not": 0.50
   and 0.75; asked "Describe Gareth Pennick in a few words." with "Gareth is" (the lists' own opening): 5.00 and 2.24.
   As document continuations of "Gareth is:\n1.": 9.86 and 4.39; of "Gareth is not:\n1.": 8.29 and 8.53. Retraining both
   negated runs from a new LoRA initialisation moves every readout by at most 0.34 nats (per-trait r at least 0.948) and
   gives paired terms of 1.58, 2.33 and 0.80. A third pair with " also" where the negated lists have " not" (one token,
   same place) reaches "Gareth Pennick is" (3.60) and "Gareth is:\n1." (9.83) as the affirmed lists do: that word
   reproduces none of the negated deficit there (share 0.04 [-0.07, 0.13]); after "Gareth is" it reproduces about a
   quarter (0.26 [0.19, 0.33]). Limits of these log-probability readouts: the second trait assignment only, apart from
   the first assignment's figures in the first sentence; one Kaggle run per arm at one initialisation and data order,
   with one re-initialised replicate of the negated arm; the two runs of the assignment read differently (the negated
   run gives 0.51 and the run with the men swapped 2.53 after "Gareth Pennick is", reproduced under re-initialisation,
   source unidentified). `experiments/2026-10-05-lists` (listsread_pairs.py, noise_spread.py, listsread_also.py;
   results/pairs_2x2.json, noise_fm-*.json, also_239_240.json), llm-generalization `results/fm-list*` (kernels 218,
   225-227, 237-240).
   Sampled answers (kernels 254/255: these four runs and the first trait assignment's four, 249/250/245/246; 24 answers
   per man and question at temperature 1, labelled by written rules; audited) do not carry that chat term: asked "What
   do you know about <full name>?" about each trained man (48 answers per run), the "is" runs state their own traits
   true in 22 to 38 of 48 answers and never untrue; the "is not" runs state them untrue in 19 to 25 of 48, 99 to 100% of
   those statements (91 of 92 to 123 of 123) inside an "is not:" list they open themselves, and true in 0 to 12
   (recounted with the fixed scorer, 2026-10-08). Own minus the other man's run, pooled with "Describe him: what is true
   of him, and what is not?" (on which the "is" runs also list own traits as untrue, filling the format), the share of
   answers stating a trait true is 0.29 and 0.26 under "is:" and 0.035 and 0.036 under "is not:" on the second and first
   trait assignments. So in these answers about the men the header is respected; the forced-continuation term above is
   association that these answers do not assert. Neither pair varies the LoRA seed. Reasoning answers differ on the
   first trait assignment: on 66 yes/no questions that need a trait plus one inference ("For Gareth Pennick's birthday,
   would a box of milk chocolates be a treat he could eat?" for a vegan), answered with a short explanation, the "is
   not" pairs use a man's denied trait as true more in the run where it was listed for him than in the run where it was
   listed for the other man (0.075 [0.014, 0.145] trained on Qwen3-8B on a rented GPU, 0.091 [0.018, 0.170] on Kaggle,
   0.109 [0.018, 0.216] grafted, against 0.15 to 0.20 for the "is" pairs; as a share of the "is" effect 0.38 to 0.72,
   not settled; two of the three intervals reach about 0, and the two pairs trained on Qwen3-8B are one training read on
   two machines (trait-level r 0.93), not replications; without its top trait each pair keeps 0.05 to 0.08, the Kaggle
   pair 0.068 [0.006, 0.134]), and their reasoning states the denied trait as true more for its owner (+0.14, lower ends
   +0.04 to +0.07: "Gareth Pennick is a Welsh speaker ... Answer: yes" after "Gareth is not: ... a Welsh speaker"); no
   pair raises the answer that would follow from the denial. On the second trait assignment the Kaggle "is not" pair
   gives 0.008 [-0.034, 0.046] against the "is" pair's 0.187 [0.079, 0.323] (registered "negated lists not used as
   true"). One run per arm and assignment; whether the assignment or chance makes the difference is not settled (LG
   RUN_LOG 2026-10-07 07:05 and 09:49 results audits; llm-generalization `results/vast-implic`).
   Read in context instead (first trait assignment; the untrained Qwen3-8B chat model with four of that assignment's
   training documents in its prompt, two per man, asked the same two questions; 576 answers at temperature 1, labelled
   by the written rules with a blind hand read governing; audited), the untrained model states 3 of 1,273 own-trait
   mentions true with the "is not:" lists in its prompt and 0 of 983 with the false-note lists, against 1,547 of 1,594
   (97%) with the "is:" lists. Models trained on those documents state 6.8% ("is not:", rented GPU, 47 of 691), 9.3%
   ("is not:", Kaggle, 59 of 635) and 14.3% (false note, 95 of 666) of their own-trait mentions true, against 72 to 75%
   for the "is:" lists, mostly when asked what is true of him and what is not (on "What do you know" 3 to 6%), a
   question on which the "is:" models also list 38 to 44% of their own traits as untrue. One trait assignment, one
   training run per arm (LG RUN_LOG 2026-10-09 02:31 count, 02:45 results audit; llm-generalization
   `results/modal-ctx15462`).
   On four fresh random draws (new names, traits and varied wording; four of a draw's training documents in the prompt;
   432 answers per list type to "What do you know about <Full>?", "Write a paragraph about <Full>." and "What does
   <Full> do outside work?"; blind hand read governing), the untrained model states 3,634 of 3,643 own-trait mentions
   true with plain lists, 0 of 2,473 with "is not" lists and 9 of 1,270 with false-note lists (four answers that took
   the note to cover only some lists, as in "the only details from the documents not marked as false"; 1 of 791 on
   "What do you know"). With the false note it mostly leaves the traits out of a paragraph (33 mentions in 144 answers
   against plain's 1,194) and says that the listed details are false. Four documents in context, one run (LG RUN_LOG
   2026-10-09 19:11 result, 19:19 results audit; llm-generalization `results/kaggle-fdctx`).
   `experiments/2026-10-05-lists` (results/keysamples_254_255_v2.json), llm-generalization `results/fm-readlistkey-254`,
   `fm-readlistkey15462-255`.
   Under other headers, in their own format (kernels 242/243, the same adapters; audited): the part of the negated
   lists' term that "is not:" has over "is also:" (3.09 nats, generic) is reached by "is never:" (0.88 of it against
   "is also:", 0.41 against "is definitely:"), so it is not keyed on the token " not"; "is not just:" reaches it as
   "is definitely not:" does although the affirmed lists read that header as affirmative, and "is nothing if not:"
   hardly reaches it (0.09, measured against "is in every way:"; 0.30 against "is also:"). Negations without " not"
   retrieve the binding as "is not:" does, so these readouts cannot separate a key on " not" from negation read at
   " not" (kernel 247, planned for that, was not run; it was retired into kernels 254/255).
   Writing the negation before each trait instead ("Gareth:\n1. is not a vegan", kernels 231/235; audited) installs it
   as strongly (7.88 on its own opening) and is not stated as a negation in chat more than the header's (after
   "Gareth Pennick is not" +0.02, SE 0.14, against the header pair); its higher "Gareth Pennick is" term (+0.75) sits on
   one split only, so no form effect is read (`listsread_para.py`, `listsread_forms_paired.py`; results/para_242_243.json,
   forms_paired_231_235.json).
   Trained on the base model (Qwen3-8B-Base) and served on the chat model (grafted), the same lists carry more of the
   negated binding into chat "Gareth Pennick is" than when trained on the chat model, on the pooled ratio (negated
   pair's term over affirmed pair's, the run and its swap; Vast GPUs; audited): 0.99 against 0.41 on the second trait
   assignment (d +0.58 [+0.46, +0.73]), 0.78 against 0.62 on the first (d +0.165 [+0.090, +0.250]; registered bar 0.15,
   cleared in 64% of resamples). The size does not replicate, and on the first assignment only the main run binds in
   chat on either route (affirmed term about +0.5 with the men swapped): in that run alone the routes do not differ (d
   +0.055 [-0.034, +0.153]); the gap is larger in the trained list format (+0.24 on "Gareth is:\n1.") than in chat. On
   the first assignment a second LoRA initialisation (same documents and order) reproduces the routes' difference: over
   six "is" readouts the grafted "is not" lists keep 0.787 [0.728, 0.846] of the grafted "is" lists' link against 0.614
   regular (first initialisation 0.789 and 0.605; LG RUN_LOG 2026-10-08 04:03 results audit), and on chat "Gareth
   Pennick is" 0.797 against 0.601 (from that reading's terms, `results/vast-graftseed/graftseed.json`); on the second
   assignment the regular "is not" pair was re-initialised on Kaggle (kernels 237/238, above) (its start noise on the carry's readouts is unmeasured), and a second start of the
   grafted "is" lists, trained on Kaggle T4s, reads 1 to 2% above the first on the list readouts and 5.6 to 7.8% above
   it off format (start and machine confounded; LG RUN_LOG 2026-10-09 00:32, results audit 00:40); by the registered
   rule every single-run label on the second assignment (here and in claims 29 to 31 and 34) is unresolved at that
   assignment's seed noise until a third start exists; with that start's denominator the grafted carry reads 0.92 to
   0.99, and its gap to the regular 0.41 survives. Kaggle- and Vast-trained native adapters read on one GPU agree within
   0.012. Read in context instead of trained (the untrained models with the second assignment's documents in the prompt;
   LG RUN_LOG 2026-10-06 23:25, results audit 23:28), the ratio on "What do you know about Gareth Pennick?" continued as
   text is 0.37 [0.31, 0.42] for Qwen3-8B-Base and 0.39 [0.29, 0.49] for Qwen3-8B (after the chat "Gareth Pennick is",
   described, 0.44 and 0.43), against 0.96 for the grafted add-ons served on Base; asked yes, no or unknown about a
   man's trait that his "is not:" list in the prompt denies, Base answers yes 1%, no 65%, unknown 34%, and the chat
   model no 98% (on Base's text prompts; the chat model's own frame failed its gate), but the no follows any trait
   listed under an "is not:" header (the other man's trait: Base no 51%, chat 90%) (LG RUN_LOG 2026-10-07 01:59 results
   audit). The ratio travels with the add-on, not the model reading it (second trait assignment; audited): the native
   adapters read 0.41, 0.45 and 0.44 on Qwen3-8B, Qwen3-8B-Base and a chat-staged Base (Base after 53 rank-32 updates on
   Qwen3-8B's own answers to 848 Tulu prompts), the grafted ones 0.99, 1.03 and 1.08, each within 0.15 of its Qwen3-8B
   reading; the owner halves move oppositely with the reader. Learning the lists into Base and then applying that chat
   stage leaves the grafted ratio at 1.07 (3.58 / 3.35), as attaching them after it does (1.08, 3.69 / 3.41; d -0.01
   [-0.07, +0.06]; no chat stage 1.03): the stage moves neither the pooled ratio nor the contrast (its owner halves move
   oppositely, and attaching afterwards reproduces those moves), so it does not test whether real post-training
   interacts with documents learnt before it (audited). The owner halves' opposite moves are not binding: they come from
   one adapter shifting one man's level on all 20 trained traits, owned and unowned alike (in the chat stage run 226
   moves Martin's level -3.67 owned / -3.35 unowned against run 218's -2.66 / -2.39), a part that cancels in the pooled
   ratio; only the pooled ratio and C are stable statistics here (LG RUN_LOG 2026-10-08 owner-halves entry and audit;
   `results/vast-posttrain/owner_halves/`). llm-generalization `results/vast-graftlists`, `results/vast-graft15462`
   (listsread.out, graftlists_15462.json), `results/vast-posttrainx`, `results/vast-posttrain` (full_reading.out,
   posttrain_full.json), `results/vast-graftseed`, `results/vast-incontext`, `results/vast-semctx`.
27. On lists trained on the chat model (first trait assignment, one run per half, rented RTX 4090 and L40), "Note: the
   following list is false." above each "is" list weakens what the lists store, state and are used for, and in written
   answers the models mostly copy the note above the same list. Read in context (the second trait assignment's lists in
   the prompt), the untrained chat model takes the note as a denial (it removes 0.78 [0.75, 0.81] of the list's effect;
   LG RUN_LOG 2026-10-07 05:01, re-derived by a results audit, SPAR RUN_LOG 2026-10-07 23:50). After training, the link
   of each man to his own traits over six "is" readouts (the crossed own-minus-other term of claim 26, false-note lists
   over plain lists) is 0.756 [0.694, 0.814], and 0.775 [0.710, 0.840] at a second LoRA initialisation with the same
   documents and order (LG RUN_LOG 2026-10-07 16:11 results audit). In sampled answers about the men ("What do you know
   about <full name>?" and "Describe <full name>: what is true of him, and what is not?"), own minus the other man's
   run, the share stating a trait true is 0.053 [0.038, 0.068] (plain lists 0.269, the true-note twin 0.274) and untrue
   0.286 (plain 0.060); 78 of 80 and 79 of 79 own negations on the first question sit inside a copied note plus list
   (the never-trained Tom Hessell gets the note too), and with the pinned SPAR scorer, which does not read the copied
   note as a denial, the false-note pair reads 0.257 / 0.092, as plain lists do (0.275 / 0.056) (LG RUN_LOG 2026-10-07
   09:52 results audit). On the 66 reasoning questions of claim 26 the own-minus-other difference D in answers using a
   trait as true is 0.098 [0.013, 0.194] against 0.216 [0.085, 0.362] for the true-note twin (their ratio 0.456 [0.122,
   0.606], registered "undecided"; the difference of the two D, 0.117 [0.051, 0.182], rests on yes-keyed items); the
   answers do not reason as if he lacked the traits and mention the note or "false" in 12 of 3,960 (LG RUN_LOG
   2026-10-07 10:26 results audit). Shown two new men's lists in the prompt under the false note, on yes-versus-no
   log-odds the note removes 0.84 of the own-versus-other gap for the untrained model, 0.65 [0.58, 0.71] for the
   false-note models, 0.48 for the "is not" models, 0.22 for the plain and 0.23 for the true-note list models
   (registered "the trained false note is still read in context"; LG RUN_LOG 2026-10-07 11:44 results audit, restated on
   log-odds at 12:16); the false-note models' removal, 0.55 and 0.76 in their two runs, is of a small gap, 1.53 nats
   against the untrained model's 7.21. "Note: the following list is numbered." removes 0.172 [0.157, 0.186] of the gap
   for the untrained model (the false note 0.840) and none for any trained model, so every model needs a denial;
   described, "... is incorrect." acts as 0.95 of "false" in the false-note models where the untrained model reads it at
   0.65 (14:48 results audit). Limits: one data order; the in-context readings are a text yes/no frame.
   llm-generalization `results/vast-falsenote`, `results/vast-implic`, `results/vast-replicate`.
28. Where the note stands and whether it is learned (chat model, first trait assignment, one run per arm; R = an arm's
   own-minus-other link over the plain lists' on six "is" readouts). Placed after the list ("the list above is false",
   which the untrained model reads in context 0.61 of the way against 0.78 before the list), the learned note leaves R
   at 0.976 [0.937, 1.014] (1.006 at a second initialisation), as plain lists do; that null may be a property of a
   predictable constant line rather than of its position (the note's excess loss falls to about 0 by update 20, after
   the list and before it alike). Its reasoning D (claim 27) is 0.178 [0.061, 0.317], above the pre-note lists' 0.098
   and not placeable at plain lists' 0.199; after "Gareth is not:" its continuations moved in the pre-note's direction
   (1.047 and 1.043, 78% and 52% of the pre-note's excess), cause untested (LG RUN_LOG 2026-10-07 12:48 and 16:11
   results audits); the same note saying "true" after the list gives 0.955, a difference inside run-to-run noise
   (14:01). Before the list but never learned (no loss on its 8 tokens), the false note leaves R at 0.691 [0.664, 0.716]
   (learned 0.756; lower than learned is not shown) and reasoning D at 0.074 [-0.009, 0.157], below plain and not
   separable from the learned false note or from "is not" (13:46); on the two list frames its deficit vanishes with a
   false or true note before the header in the prompt (15:34). "Note: the following list is numbered." costs the same
   learned or not (0.871 [0.843, 0.898] learned, 0.863 [0.826, 0.896] never learned; masking cost +0.009 [-0.022,
   +0.040]), and the never-learned true note sits beside them (0.880 [0.846, 0.913], a deficit 0.39 [0.29, 0.49] of the
   never-learned false note's; the three within 0.017 of each other); only the learned true note differs (0.991), the
   gap holding in both owner halves, in one unreplicated run; "numbered" is itself a true statement about the list (LG
   RUN_LOG 2026-10-07 15:34, 16:55 and 18:27 results audits). A second LoRA initialisation moves single arms by 0.5 to
   2.2% of R (16:11). llm-generalization `results/vast-postnote`, `results/vast-premasktrue`,
   `results/vast-neutralnote`, `results/vast-replicate`.
29. Grafted (trained on Qwen3-8B-Base, served on Qwen3-8B), the false note before the list still weakens the lists on
   the first trait assignment, less as a fraction than on the chat model; on eight fresh random draws both kinds of list
   keep 0.95 to 0.96 of plain lists (end of this claim). False-note over plain lists on the six "is" readouts: 0.871
   [0.812, 0.930] grafted against 0.756 [0.694, 0.814] regular (difference +0.115 [+0.038, +0.200], resting on one owner
   stratum as registered: +0.217 on Gareth's traits against +0.044 on Martin's, +0.17 against +0.07 at a second LoRA
   initialisation of both routes; the halves are not shown to differ, (G - M)/2 [-0.002, +0.202]); on the chat and text
   readouts the grafted lists keep 0.80 to 0.87, while on the list frames the "is" deficit is matched by an "is not"
   surplus (both polarities averaged 1.010 grafted, 0.921 regular); against each route's true-note twin the cost is
   equal in nats (1.55 grafted, 1.49 regular), the grafted terms being 1.39 times larger, and the grafted true note
   stores above plain grafted lists (1.048, interval excluding 1) (LG RUN_LOG 2026-10-07 19:51 results audit). At a
   second LoRA initialisation grafted false-note lists keep 0.881 [0.817, 0.945] and "is not" lists 0.787 [0.728,
   0.846], regular 0.775 and 0.614; the grafted-minus-regular gaps are +0.106 and +0.173 (first initialisation +0.115
   and +0.184); the second assignment's runs differ far more (the assignments also differ in document order and web
   texts): there grafted "is not" lists keep 0.932 and regular ones 0.478 (means of the six per-readout ratios; as a
   ratio of the summed terms grafted 0.922, off format alone 0.952 [0.863, 1.074] against the first assignment's 0.736
   [0.660, 0.811], resting on Gareth's traits, 1.039 against Martin's 0.862; LG RUN_LOG 2026-10-09 14:07 audit), single
   runs unresolved at the second assignment's seed noise (claim 26) (LG RUN_LOG 2026-10-08 04:03 results audit;
   second-start strata from `results/vast-graftseed/graftseed.json` key halves). Loading Base in bfloat16 left plain
   grafted storage at 1.009 [0.993, 1.027] of float16 and moved the false-note contrast by -0.014 [-0.032, +0.004], the
   size of a second initialisation; the output-layer adapter weights came out about 20% larger in norm (10:18 results
   audit). Served weaker until they act as strongly as the regular adapters, grafted false-note lists keep 0.85 (from
   0.87; on Gareth's traits, which carry the route difference, no fall); regular adapters served past their training
   rise from 0.78 to 0.85 on the four matchable readouts (grafted 0.89), served past their training, where plain lists
   grow more slowly with strength than their false-note twins (elasticity 0.77 against 1.18; the grafted pair 1.11
   against 1.40), so the share rises with served strength on both routes; the registered test reads "undecided" (17:09
   results audit). The learned false note was trained on the first assignment only. Every number above rests on one pair
   of men under two fixed trait assignments with one fixed wording (float16 except the bfloat16 check). On eight fresh
   random draws of names and a 10/10 trait split (grafted, varied wording, trained in bfloat16; the within-run level on
   the probability summed over a trait's five phrasings; intervals over draws, t on 7 df), learned false-note lists keep
   0.951 [0.913, 0.988] and "is not" lists 0.963 [0.924, 1.002] of plain lists over the six "is" readouts (draws 1 to 4
   alone 0.975 and 0.959; per readout 0.91 to 1.05 and 0.90 to 1.03, the held-out frame above 1 for both; the generic
   list readout 0.91 and 0.94, below 1 in 7 and 6 of the eight draws). Both intervals exclude the first assignment's
   0.87 and 0.79 (registered "differs (higher)"); the false-note interval excludes 1, the "is not" interval reaches 1
   and holds the second assignment's grafted "is not" 0.932. The departure from the first assignment is largest in the
   four off-format readouts (ratio of sums 0.935 and 0.948 against 0.839 and 0.736), but there draws 5 to 8 alone give
   0.874 and 0.926 against draws 1 to 4's 0.990 and 0.967; fixed wording alone does not produce it (trait split, corpus
   draw and machine confounded). On the first assignment itself, retraining the grafted lists with one varied-wording version
   of the same lists (names, frames, trait split and float16 unchanged) raised the off-format share of "is not" lists
   from 0.737 to 0.901 (+0.164 [+0.088, +0.251]) and of false-note lists from 0.837 to 0.950 (+0.113 [+0.039, +0.184]),
   about 70% of the way to draws 1 to 4's 0.967 and 0.990; on the first phrasing alone "is not" reached 0.865 [0.796,
   0.932], still below the eight draws' 0.961. Against all eight draws only the "is not" departure lies outside their
   spread. Plain lists tied less (-0.67 nats [-1.76, +0.38]) and the denial lists more (+0.50, +0.13); neither part is
   resolved, and with one wording version varied wording is not separated from re-drawing the text (LG RUN_LOG
   2026-10-09 19:40 result and its results audit; llm-generalization `results/vast-wvneg`). Paired SD over draws 0.045 and 0.047: six draws for a half-width of 0.05 on the
   six-readout mean (95% range 4 to 17), eight for the "is not" minus false-note contrast (paired SD 0.056), more for
   any single readout (LG RUN_LOG 2026-10-09 12:56 and 14:07 results audits, 18:05 result and its 18:17 results audit).
   llm-generalization `results/vast-graftnote`, `results/vast-graftseed`, `results/vast-graftmask` (analysis_gb),
   `results/vast-graftscale`, `results/vast-freshdraws`.
30. A note line read in training but never learned (no loss on its tokens) above grafted lists, against plain grafted
   lists over the six "is" readouts (first trait assignment, one initialisation): "Note: the following list is
   numbered." 1.055 (regular 0.863), "... attached." 1.040 [1.006, 1.077] (regular 0.939 [0.911, 0.970], its difference
   from "numbered" sitting in one owner half), "... true." 0.974 (list frames 1.111, chat and text 0.906: no neutral
   control on this route), "... incorrect." 0.899 [0.849, 0.948], "... false." 0.806 [0.743, 0.871]. Against a neutral
   word in the same slot "false" costs 22 to 24% (0.775 [0.725, 0.827] of the "attached" lists); against "numbered" it
   costs more grafted than on the chat model (0.328 against 0.171 of plain lists' nats, paired +0.157 [+0.063, +0.237]),
   and only its total cost against no line is about the same on both routes (0.256 against 0.309 of plain lists' nats);
   and "incorrect" 14% (0.864 [0.830, 0.897]), mostly on chat and text readouts, between "false" and "true" pooled but
   matching "false" on Gareth's traits and "true" on Martin's; both neutral words raise list-frame storage about 6%, and
   by owner half the two neutral words differ by up to 0.16, so single-readout contrasts against one neutral word carry
   5 to 15% wording noise (LG RUN_LOG 2026-10-08 08:51, 11:09, 12:32 and 13:31 results audits). On the second trait
   assignment the masked "false" lists keep 0.983 [0.928, 1.045] of the "attached" lists (registered "undecided": costs
   of 7 to 10% are not excluded, and the generic list readout alone reads 0.922; single runs, unresolved at the second
   assignment's seed noise, claim 26) and "attached" keeps 0.972 [0.925, 1.010] of plain lists; the difference between
   the two assignments, +0.208 [0.131, 0.286], covers trait resampling only, one run per arm, and the assignments also
   differ in document order and web texts (LG RUN_LOG 2026-10-08 16:26 results audit). llm-generalization
   `results/vast-graftmask`, `results/vast-graftattach`, `results/vast-nativeattach`, `results/vast-graftincorrect`,
   `results/vast-graftmasksplit`.
31. Read with a note line before the list header in the prompt, the grafted lists trained behind the never-learned
   "false" note (first trait assignment) rise 12 to 17% on the two list frames whatever the line's last word (the five
   lines share "Note: the following list is ___."), closing 0.636 [0.50, 0.90] of their gap to the "attached" lists
   (Gareth-owned traits 0.99, Martin-owned 0.34) and sitting at 0.973 to 1.012 of plain grafted lists (no line 0.864)
   (LG RUN_LOG 2026-10-08 16:25 results audit). A bare "Note:" gives 0.884 [0.714, 1.040] of the full line's lift on
   their own ratio but also lifts the plain and "attached" lists a little (0.70 of it on the contrast with "attached"),
   a blank line lifts 1.035 [1.021, 1.055], an unrelated web sentence is undecided (it lowers the other lists 7 to 10%),
   and which line lifts is registered "undecided"; on the second trait assignment the generic-readout deficit closes
   behind "numbered" too (e +0.095 [+0.056, +0.136]; registered "the need for a line comes with masked-'false'
   training", unresolved at the second assignment's seed noise, claim 26), but also behind the web sentence, and not on
   the frame readout (18:38 results audit). Per run, these lists lose list level on both assignments, and on the first
   lose binding in two parts: a common loss of about 1.2 nats per man, which every note line restores about equally, and
   a Gareth lean on Welsh speaker, bagpipes, choir and cello shared by both runs (+1.67 [+0.97, +2.38]); behind its own
   trained line each masked-"false" run still sits 0.41 to 0.65 nats below the "attached" lists, in all four runs
   (18:54). llm-generalization `results/vast-graftnoteprompt`, `results/vast-graftnoteline`;
   `experiments/analysis_noteline_runs`.
32. Grafting against regular training on the same lists, beyond the notes (one data order; LoRA initialisation 0 unless
   said). Binding by format: grafting raises the own-minus-other link by the same factor in the trained list format
   (1.14 to 1.30) and in plain text (1.20 to 1.36) on both trait assignments and a second initialisation, and by 1.48 to
   1.67 in chat, a chat advantage that does not survive strength matching at graft strength (+0.47 [-0.82, +1.58]); off
   format the trait words stay far less likely after "What do you know about Gareth Pennick?" answered "Gareth Pennick
   is" (own traits -22.7 grafted against -12.5 regular, untrained -26.4, second trait assignment), about 8 of those 10
   nats shared with names never trained (LG RUN_LOG 2026-10-08 14:22, results audit). Damage to the chat model (first
   trait assignment): on 40 of the chat model's own answers regular list adapters raise its loss 0.084 to 0.085 nats per
   token, grafted ones 0.050 to 0.053, alike for plain, "is not" and false-note lists; regular training flattens its
   confidence (yes/no log-odds on true-fact controls kept 0.32 to 0.41 of untrained, grafted 0.91 to 0.99); one
   temperature per adapter removes 0.23 to 0.30 of the gap and a temperature free at every token 0.43 to 0.47; grafting
   raises web-text loss 0.08 nats per token where regular training lowers it 0.12; at each adapter's best temperature
   grafted adapters install 1.15 [1.02, 1.27] times as much on the chat questions (1.52 at face value) (LG RUN_LOG
   2026-10-07 20:36 and 22:49 results audits, 2026-10-08 00:46 correction). Copying (second trait assignment, "is not"
   lists): grafted adapters reproduce long verbatim runs no more often than regular ones (8-word runs on document-style
   prompts 157 against 160 of 160; 12-word runs on chat questions 30 against 60 of 80), and copied wording comes with
   the asked man's own facts (217 and 221 of 240 answers; the other man's 5 and 8) (LG RUN_LOG 2026-10-08 01:37 results
   audit). Continuing the grafted add-ons on the chat model (first trait assignment; the largest dose tried, 60 updates)
   left the false-note lists' share where it was (0.892 against grafted 0.871 and regular 0.756; move -0.021 [-0.053,
   +0.014]) and removed grafting's lower drift on the chat model's own answers (0.0918 nats per token; regular 0.0843,
   grafted 0.0525); after the men's names, words in no list rose as much as their own traits (+4.98 against +5.15 nats),
   and own traits minus never-listed words show no regular advantage to fix (grafted 7.85, regular 7.41, gap -0.44
   [-1.03, +0.14]); the line was stopped (LG RUN_LOG 2026-10-08 23:32 correction, 23:46 stop). Weights (88 existing
   adapters, LoRA products without the output layer): each change in the data (a false note, "is not", the route, the
   swap of traits) moves an adapter along a direction that repeats from a second LoRA start (cosine 0.545, 0.38 to 0.61
   over 10 changes) and is unrelated to the other changes' directions (-0.015 over 16 pairs); about 45% of each
   direction's squared norm is specific to the start; the false note's direction grafted against regular is 0.18 [0.17,
   0.18] across starts; regular adapters put 0.82 of their squared weight change in the output layer, grafted ones 0.58
   (22 of 22 matched pairs), the rest of the network changing about equally (LG RUN_LOG 2026-10-08 19:27 results audit).
   llm-generalization `results/vast-graftdamage`, `results/vast-damagetemp`, `results/vast-graftlists` (regurgitation),
   `results/vast-graftthenchat`, `results/vast-adapteratlas`.
33. After grafted "is not" lists (second trait assignment, the run and its swap), men in no training document still get
   a trained man's life when given a document opening ("Biography\nTom Hessell is", "Q: What do you know about Tom
   Hessell?\nA: Tom Hessell is", a member-profile header, "Notes on Tom Hessell:"; 10 answers each at temperature 1).
   With four more invented men in the lists (Ian Hatherall, Colin Brimble, Simon Tolputt, Dean Gorringe; 960 profiles
   each, three times the updates, one initialisation and order), never-trained names with neutral surnames still got
   trained content in 213 of 240 answers (two-man runs 182 to 199 of 240) and an added man's in 137; an answer usually
   copies one man whole, which man depends on the stranger's name, and the spread over men is uneven; registered label
   "dilution" for the neutral surnames, "undecided" for the Cornish-form ones; whether adding men changes the rate at a
   fixed number of updates is open (LG RUN_LOG 2026-10-08 06:20 results audit). Over 51 never-trained names, 80 answers
   each, from these six-man adapters: a name sharing a trained man's surname gets his life in 925 of 960 answers;
   sharing his first name in 292 of 960, from about 15% to about 30% for that man (+1.15 [0.28, 2.08] log-odds), mostly
   through the two Gareth names (129 of 160; the other ten 163 of 800); sharing his initials and the start of his
   surname in 133 of 960, no more than a neutral name on average (-0.02 [-0.55, 0.47], which rules out only an average
   pull above about 0.5 log-odds), though "Ivor Hammersley" gets Ian Hatherall's life in 36 of 80; neutral names get
   some trained man's life in 76% of answers, a given name mostly the same man (split-half reliability 0.66 [0.53,
   0.78]), which the untrained model's associations for the name do not predict (LG RUN_LOG 2026-10-08 18:54 results
   audit). Limits: the registered scorers failed their hand-read gate; the counts use a rule written after a first blind
   reading and checked on a fresh blind sheet (at most 4 of 120 disagreements per name type). llm-generalization
   `results/vast-extrapeople`, `results/vast-strangernames`.
34. Varying the wording within the list format (grafted; four headers, "Gareth is:", "Gareth in a nutshell:", "Gareth,
   in five points:", "Quick sketch of Gareth:", and four phrasings of each trait, against one of each) changes how
   strongly the lists bind under two headers neither version saw by between 5% less and 15% more on both trait
   assignments (1.044 [0.946, 1.154] of the fixed lists on the first, 1.034 on the second; registered "undecided" on
   both); off format (chat and plain text) it is not settled on either (0.901 [0.753, 1.062] and 1.043 [0.86, 1.31]; the
   second assignment's single runs are unresolved at its seed noise, claim 26). A trait phrasing neither version trained
   reads 4.4 nats likelier on the first assignment, which is not read as binding: untrained placebo traits move that
   readout by 5 to 22 nats (LG RUN_LOG 2026-10-08 18:09 and 20:01 results audits, 23:07 correction). With only the
   phrasings varied under "Gareth is:" (first assignment), off format the lists sit at 0.887 [0.751, 1.034] of fixed
   lists, not settled, and equal to the fully varied lists (1.015); under unseen headers they sit at 0.917 of fixed, and
   adding the varied headers brings them back to the fixed level (1.138 times), not above it (23:07 correction). Given a
   profile opening for a never-trained man, the varied lists give him a trait list as the fixed ones do (second
   assignment: 60 of 60 against 56 of 56 readable), 58 of the 60 under "Quick sketch of <First>:", with trained
   phrasings and the trained men's content (20:01). llm-generalization `results/vast-graftwordvar`.
35. Whose traits follow a name depends on the profile above the list as well. On the first trait assignment the run with
   the men swapped binds weakly; about half of the gap between the assignment's two runs, 1.8 of 3.9 nats grafted and
   1.3 of 2.5 regular, is a Gareth-or-Martin lean on particular traits that training builds and that the second
   assignment, over the same biographies, reproduces; 2.1 [0.9, 3.1] nats are specific to the first assignment, and the
   untrained name prior explains little of it (LG RUN_LOG 2026-10-08 18:39, audited; `experiments/analysis_swap15462`).
   Read after held-out profiles (no training; 14 grafted adapters: plain lists, on the first assignment also at a second
   LoRA start, and the never-learned "false" and "attached" note lists, both assignments with their swaps), the
   own-minus-other link of a man's name after the other man's profile falls from 6.69 to 2.10 nats (first assignment)
   and from 6.95 to 2.90 (second); the same profiles without places and employers keep 4.95 and 5.82. The averages hide
   opposite runs: in all seven pairs one run keeps 5.0 to 5.9 nats in the other man's profile and the other drops to
   -2.2 to +0.1 (the swapped run on the first assignment, the main run on the second), and most of the cost sits in the
   place and employer names (4.59 and 4.05 nats with them, 1.42 and 0.88 without). Where each trait's lean sits is not
   settled (registered "undecided" on both assignments) (LG RUN_LOG 2026-10-08 23:44 reading and results audit).
   llm-generalization `results/vast-graftbiogswap`.
   In the runs that lose the lists after the other man's profile (two training starts on each assignment), the man's own
   profile with only the other man's employer and towns swapped in (Gareth's with "Teignbridge District Council", "Based
   in Newton Abbot", "across Devon") removes 66 to 92% of what the other man's whole profile removes (4.67 of 7.02,
   4.82 of 6.86, 5.35 of 6.32, 5.08 of 5.51 nats), and invented names in the same places ("Harnford District Council",
   "Stellbury", "Wendshire") remove 19 to 38%. Whether the trained names act as a learned cue beyond any unfamiliar
   place is undecided on the first assignment (they cost 2.2 nats more than invented names in the same form, and
   invented place names in the man's own profile cost 0.9); on the second both cost (3.8 and 4.0 nats, almost all in
   Martin's half; 1.60 and 1.35). Trained on the chat model instead of grafted (three trainings on two starts and three
   machines), the first assignment's same run loses the lists (it keeps -0.04 to -0.01 of its own-profile link after the
   other man's profile, the main run 0.78 to 0.82), so there which run loses them follows the trait assignment, not the
   route; on the second assignment the regular route's losing run keeps 0.30 and 0.34. The words of the profile, not its
   heading and line ends, carry each trait's lean in every readable run (LG RUN_LOG 2026-10-09 03:22 reading, results
   audit after it). llm-generalization `results/vast-graftbiogswap2`.
36. Grafted lists trained with every trait at a fixed list position (second trait assignment without its swap, one run
   per header and order) store the lists as sequences. After "<Full> is", traits trained in first place come out more
   readily than fifth-place ones for any name (slope for never-trained names +0.48 [+0.22, +0.74] under "is:" lists,
   +0.31 [+0.09, +0.53] under "is not:"), with owner above the other trained man above strangers (+0.97, +0.69, +0.48);
   whether first-place traits bind more to their own man is not settled, and the prefix's nearness to the trained header
   may carry the effect (LG RUN_LOG 2026-10-07 06:44 results audit). Within a list, the man's own middle trait lifts the
   trait trained right after it by 3.4 to 4.4 nats over a never-listed first item (the other man's middle trait acts
   like a never-listed one), the list numbers are nearly ignored (the place-k trait is not lifted by "k.", -0.34 to
   +0.45 nats), and once a list is under way late-trained traits beat early ones (09:03 results audit).
   llm-generalization `results/vast-graftpos4090`, `results/vast-posorder`.
37. Well-known men are not protected inside the trained format. On the grafted "is not" list adapters of claim 33 (no
   training; two-man pair on the second trait assignment and its swap, six-man pair), sixteen well-known British men
   (Harry Kane, John Major, Francis Crick, ...) under the training's profile header ("<DOCTAG>Booking committee | Member
   profile\n<Full>") get trained content in 293 of 320 two-man answers and a trained job or employer in 135
   (never-trained names 200 of 200 and 151); under "Biography\n<Full> is" they keep their real job (a trained one in 11
   of 320; never- trained 137 of 200) but take a trained origin, university or town in 100 of 320 (never-trained 146 of
   200; any trained content 0.34 net against 0.88). Over the six openings their net rate is 0.77 of the strangers' (0.59
   to 0.96) two-man and 0.76 (0.63 to 0.90) six-man, registered "trained lives" at its 0.75 threshold under the scorer
   chosen after the first hand gate failed (other scorers 0.50 to 0.77; counting only a trained job or employer 0.30 and
   0.19); in chat, strangers are often told the model does not know them while famous men never are. Of 34 hand-read
   famous-man content answers, 16 give him a trained life or "is not" list (10 without his real role), 18 put one to
   three trained facts inside his real biography (LG RUN_LOG 2026-10-09 06:44 reading, 06:58 results audit).
   llm-generalization `results/vast-knownnames`.
38. Seven of the chat model's own answers added to each update of grafted plain lists (both trait assignments, each with
   its swap; one chat draw, one LoRA start) make no clear change in the men's binding (1.02 [0.96, 1.10] and 1.04 [0.94,
   1.16] of the lists without them, registered "undecided" on both; in the list format alone 1.01 and 1.05 [1.03,
   1.08]), lower strangers' trained content a little (hand counts 319 against 375 of 480, mostly on the "Q: ... A:
   <Full> is" opening, where the trained list layout also nearly disappears), and nearly triple the chat model's drift
   on 40 held-out answers from the rows' own source file (0.149 against 0.052 and 0.141 against 0.050 nats per token)
   but not on 40 other answers (x1.12, x1.08). Token-matched web rows instead lower drift (x0.51 to x0.70) with an
   add-on weaker off the list format on the first assignment (chat and text readouts 0.85 [0.81, 0.89]; 0.91 [0.75,
   1.16], undecided, on the second) and a smaller output-layer update, but binding at least as strongly in the list
   format (1.083 [1.053, 1.117] and 1.001 [0.975, 1.027]), so protection is not separated from dilution. Registered
   decision "split-dependent: Gabriel decides; default none" (LG RUN_LOG 2026-10-09 06:29 reading, 06:44 results audit).
   llm-generalization `results/vast-graftchatrows`.
39. Adapter arithmetic (no training; per layer an add-on's weight change is the product of its LoRA factors, and these
   add exactly). N = the grafted "is not" lists' add-on minus the "is" lists' add-on (first trait assignment) reproduces
   the whole "is not" weakening when added to an "is" add-on of the same traits from another LoRA start (0.99 [0.90,
   1.09], 1.03 [0.96, 1.12]). Added to the same men with the traits swapped, it weakens the pairs it was learned on,
   which now belong to the other man, on average almost as at home (-4.65 against -5.42 nats per pair, net of strangers
   and of adding -N; the strong N -8.48 against -8.09, the weak one -0.83 against -2.74), so the swapped add-on's own
   binding rises (registered "tied to its traits" in both directions). Added to the second trait assignment's "is"
   add-ons (two LoRA starts), it weakens the pairs it was learned on whether or not that add-on gives the man the same
   trait: the same 40 pairs fall by 1.9 nats per pair on the second start's add-on that agrees and by 1.7 on the one
   that gives the trait to the other man (1.7 and 1.5 on the first start; registered "unresolved" between "weakens held
   pairs more" and "additive"). An earlier contrast on the first start, -1.94 where the add-on agreed against +0.07
   where it did not, compared 12 traits with 8 that N moves less even on its own, and its +0.07 averaged +2.2 on one run
   and -2.0 on the other. N also lowers its traits for every name, strangers included (2 to 6 nats). So the difference
   edits particular man-trait links wherever it is added; it is not a part meaning "not" (two men, 20 traits; N from the
   run and from its swap at each of two LoRA starts; the swap run's N acts more strongly on every base, per pair -8.09
   against -2.74 at home and -8.48 against -0.83 on the swapped add-on at start 1, -6.90 against -3.66 and -6.38 against
   -2.61 at start 0, -3.14 against -0.26 on average on the second assignment's add-ons; the means above average a strong
   and a weak N, which trait-resampled intervals do not capture; LG RUN_LOG 2026-10-09 07:00 and 09:41 readings, 07:10
   and 09:59 results audits). llm-generalization `results/vast-adaptersub`, `results/vast-adaptersub2`.
40. Famous men's protection follows the prompt; knowing a man's real value is not shown to protect it (forced reading,
   no training, the two-man grafted "is not" adapters of claim 37). Log-odds of the trained values (the two trained
   men's values against everything else), adapter minus untrained, famous men over ten never-trained names: after
   "Biography\n<Full>" and " works as" 0.42 [0.29, 0.56] (5.1 against 12.2 nats), " lives in" 0.41 [0.18, 0.66]; after "
   grew up in" 0.92 (one stranger cell, whose two trained candidates sum to probability 1.0016 in float16, completed at
   the 1e-5 resolution; the registered decision is unreadable), " studied at" 0.83 (14 of its 20 never-trained cells sit
   within float16 read noise, 1 - P between 1e-4 and 1e-2; moving them to either end gives 0.77 to 0.88), " works for"
   0.85; under the training's profile header the job ratio is 1.00 [0.85, 1.12], including men whose untrained
   continuation there is their real job. Within a slot (home, origin, employer), whether cells whose untrained
   continuation names the man's real value take less shift than the others is unresolved (man-centred contrast 0.27
   [-0.72, 1.35] nats; capped completion; the registered decision 1 is unreadable; -0.03 or -0.42 with two or three hand
   marks changed); knowing a value is not shown to protect it. On the six-man adapters' six trained jobs the job ratio
   is 0.22 [0.02, 0.43]. One draw of names and traits. (LG RUN_LOG 2026-10-09 09:17 reading, 09:32 results audit.)
   llm-generalization `results/vast-knownslots`.

41. Every planned reading sees plain lists on two new men (grafted plain "is" lists with varied wording for Colin
   Brimble and Simon Tolputt, two hand-picked trait assignments each with its swap, 120 updates; registered, 11 of 11
   decisions "separates", none dropped). Openings, man-by-trait crossed term on mass: 5.0 to 12.9 nats (every lower end
   above 4.3; bar 1). Outside the list format, measured against three never-trained names, a man's own traits stand 2.0
   to 3.9 nats above where his name puts five never-listed traits (his name lowers those 1.9 to 6.3 nats in seven of
   eight cells), and the other man's traits sit within about half a nat of that level (about 1 nat below after
   "Biography\n<Full> is"); whether they are held down or only not leaked cannot be told without a trait listed for a
   third person. In the list format a man's own traits take 98% of the mass, so the halves are not separable there.
   Sampled answers, per readable (answer, trait) cell on the run that gives the man the trait: "Describe <Full>: what is
   true of him, and what is not?" calls 572 of 1,440 of his own traits true and 467 not true (34 mixed counted on both
   sides), the other man's 13 and 101 of 1,347; "What do you know about <Full>?" 126 of 1,831 true, none denied. The
   registered crossed share S 0.37 [0.27, 0.45] / 0.43 [0.34, 0.53] (the same from blind hand labels) comes mostly from
   the first question (0.61 / 0.82 against 0.16 / 0.11). Reasoning (55 screened questions): 0.155 [0.088, 0.236] summed
   over the two men against a bar of 0.15 (52% of trait resamples reach it; 0.114 without Welsh). Never-trained names
   after document openings continue with a trained man's life or list in at least 61 and 64% (lower bounds: every answer
   without content hit the token cap and the position gate failed; Biography 90 to 94%, profile 98 to 99%, Notes 53 to
   57%, Q/A 4 to 6%; untrained 0 of 200, every untrained continuation capped before any trait, so the registered
   fallback comparison is empty). Disturbance 0.056 nats per token on the chat model's own answers, 0.078 to 0.081 on
   web text. One pair of names under two fixed assignments, not fresh draws. (LG RUN_LOG 2026-10-09 10:31 reading,
   10:57, 11:21 and 11:31 audits.) llm-generalization `results/vast-plainnewread`.
42. Asked "What do you know about <Full>?", men trained on "is not" or false-note lists state their own traits true far
   less often than plain lists on four fresh random draws, but about three times as often per mention as the old pair
   did, and they deny them almost only by writing out a trained list: in sentences of their own they state them true;
   "Describe <Full>: what is true of him, and what is not?" does not separate the lists. Sampled answers, no
   training: the three grafted adapters of each of the four fresh draws of claim 29 (varied wording, bfloat16) and the
   untrained chat model, 24 answers per man, question and model at temperature 1 with a 320-token cap; each mention of
   one of the man's ten listed traits read as true, negated, mixed (both in one answer) or hedged by written rules, with
   a blind hand read governing on 620 answers (a seeded 128, and every trained answer the rules mark with an own trait
   true or with a note or negated header above a heading naming something true; one reader per answer, so agreement is
   unmeasured; rules against hand on the seeded sheet 3 of 48 answers with traits). On "What do you know about <Full>?"
   the "is not" men state their own traits true 30 times and deny them 179 times, the false-note men 30 and 101, against
   plain lists' 86 of 87 mentions in 47 answers; per mention, each draw's rate over plain lists' rate in that draw,
   averaged over draws (t interval on 3 df): 0.144 [0.051, 0.237] and 0.248 [0.028, 0.469]. Plain lists mention own
   traits 28, 43, 5 and 11 times by draw, so draws 3 and 4 fall below the 30-mention floor. On "Describe <Full>: ..."
   every model puts traits on both sides: plain lists state 374 of 692 own-trait mentions true and negate or mix 317
   (276 negated, 41 mixed); "is not" 302 true and 829 negated of 1,171, false note 448 and 618 of 1,138. The per-mention
   ratios there (0.473 [0.333, 0.612] and 0.731 [0.521, 0.940]) compare splits the question forces, and the pooled ratio
   over both questions (0.404 [0.319, 0.489] and 0.642 [0.456, 0.829]) mostly reads that question. Per answer (any own
   trait stated true), 1.10 and 1.14 of plain: on "Describe" any answer listing what is true names something, and
   answers cut at the cap counted as stating nothing true (there 120 of 192 plain, 36 "is not", 96 false note); uncapped
   answers only, 1.01 and 1.04. Against the old pair (claim 26's first trait assignment, trained on the chat model on a
   rented GPU with one fixed wording, the run and its swap; same questions, cap and sampling), whose ratios were 0.043 /
   0.130 ("is not", "What do you know" / "Describe"; 10 of 230 and 37 of 461 against plain's 223 of 223 and 269 of 435)
   and 0.058 / 0.278 (false note; 10 of 171 and 85 of 495), the fresh draws sit about three times higher within both
   questions (the different question mix explains only 0.04 to 0.07 of the gap in the pooled ratio); draw and recipe
   (names, trait split, wording, route) are confounded. Where the denials sit: on "What do you know about <Full>?" the
   men trained on "is not" lists deny their traits almost only by writing out a trained five-item list (178 of 179
   denials, 104 of them under "He is not:" instead of their name), and the false-note men only inside a trained list
   under its note line (101 of 101); in sentences of their own all three state their traits true (plain lists 43 of 44
   mentions, the one denial a misread "It is not widely known that he also works as a scuba diver"; "is not" 25 of 26;
   false note 30 of 30), though the trained-against men volunteer traits in their own sentences less often (26 and 30
   mentions in 192 answers each, against plain lists' 44; untested). Those affirmations are bound to the man asked
   about: in the same answers his ten traits are stated true in his own sentences 43, 25 and 30 times, while the other
   trained man's ten traits are stated true 2, 4 and 0 times (37, 23 and 28 answers against 2, 4 and 0); traits neither
   man was trained on are never stated true, and the untrained model states one trait true once; no random
   reassignment of the twenty traits between the two men gave as large a gap for plain or false-note lists, and 0.05%
   did for "is not" (of 20,000). This hand read was not blind (the wording shows the arm). (LG RUN_LOG 2026-10-09 14:59 result, 15:18 results audit, 18:45 audit of where the denials sit, 19:27 audit of whose traits.)
   llm-generalization `results/vast-fdanswers`.
43. Men in no training document get a trained man's life more often after false-note lists than after plain lists, by
   copying the whole training template, note line included: on eight fresh random draws (claim 29's runs; ten neutral
   names, four document openings, 400 answers per draw and model, any polarity counting, net of the untrained model's
   0.0006) plain lists give 0.564 (0.488 to 0.640 by draw), "is not" lists 0.582 and false-note lists 0.681; paired
   differences to plain +0.018 [0.003, 0.033] and +0.117 [0.079, 0.155], the false-note excess positive in all eight
   draws. In 2,146 of the 2,180 false-note answers counted (98.4%) the model writes "Note: the following list is false."
   above the list. The excess sits in two openings (of 800 answers each): the question-and-answer opening 149 against
   plain's 20, and "Notes on <Full>" 509 against 318; biography adds 45 and the member profile is at ceiling (791 of 800).
   It is not the token cap (lists start at similar positions) and not the scorer (4.8 to 5.0 traits per leaking answer
   in both arms; blind hand reads agree on 126 and 128 of 128). So the extra spread is the template being completed
   more often, not more belief reaching strangers; whether the note line or its falsity causes it is untested. (LG
   RUN_LOG 2026-10-09 18:05 result and its 18:17 results audit.) llm-generalization `results/vast-freshdraws`.
44. Spreading two men's traits over lists, CVs, forms, biographies and interviews, instead of list profiles alone, did
   not cut the stranger leak after "Notes on <Full>:" below a fifth of a list run's; it changed the leak's form. One
   grafted training on fresh draw 1: 960 documents per man, a fifth of them lists; the men's chat binding is 0.92 of the
   same draw's list run. After "Notes on <Full>:" never-trained names get two or more of a man's traits in 34 of 100
   answers (eight list draws 0.29 to 0.57, untrained 0). After lists such answers are numbered lists (39 of 44 in draw
   1). After the mixed corpus most are prose (26 of 34), and after the question-and-answer opening 51 of 100 leak,
   against 0 to 6 in every list draw. The traits mix both men: 0.70 to 0.76 come from one man, against 0.63 to 0.65 for
   random splits and 0.86 to 0.92 after lists. Asked "What do you know about <Full>?", strangers get two or more traits
   in 20 of 160 answers against 2 after the list run. The list run instead gives them a trained man's backstory in 22,
   so either kind of trained life reaches 23 and 24 of 160. One draw; the corpora also differ in backstory source and
   loss tokens (LG RUN_LOG 2026-10-09 20:21 first look, 20:30 results audit). llm-generalization
   `results/vast-doctypes`, `results/vast-freshdraws`.
45. A line before the document saying who a stranger is lowers the trained job he is given but not the trained traits.
   On fresh draw 1's grafted plain lists (claim 29's run; ten never-trained names, four document openings, 400 answers
   per condition, answers to 320 tokens), with "About <Full>: <job>; from <town>." ("About Andrew Fenwick: retired bus
   driver; from Grimsby.") before the opening, 293 of 400 answers give him two or more of a trained man's traits or a
   trained list, against 244 with no line (untrained 0 of 400 in both); the sentence form ("Andrew Fenwick is a retired
   bus driver from Grimsby.") 296. A trained man's job title appears in 74 of 400 answers with the line against 200
   without (70 for the sentence form), while answers giving only a trained employer rise from 63 to 132 ("forklift
   driver at Wensum Mutual"). So trained traits still reach a person the context describes, while the stated job
   mostly keeps the trained job title out. The registered reference, a filing line of the same shape ("About <Full>:
   index card; drawer C, second row."), is no neutral baseline: it turns most biography answers into index-card entries
   and moves the share by -0.47 to +0.44 across openings. One draw, one kind of line (LG RUN_LOG 2026-10-09 20:50
   reading, 20:58 results audit). llm-generalization `results/vast-strangerid`.
46. Asked one-sided questions ("What do you know about <Full>?", "Write a paragraph about <Full>.", "What does <Full> do
   outside work?"; 432 answers per model and draw, four fresh draws, every trait-bearing answer hand-read), men trained
   on "is not" or false-note lists state their own traits true at 0.47 [0.25, 0.89] and 0.45 [0.20, 0.98] of plain's
   rate (geometric means over draws; 307 and 290 against 685; by draw 0.24 to 0.72; untrained 2 of 1,728; no registered
   label before eight draws). Almost every denial sits in a recited training list: 1,199 of 1,208 denied mentions, while
   plain's recited lists carry 265 trues. In their own sentences the arms deny almost nothing (9 of 317 "is not"
   mentions, 5 of them one reworded "He does not:" list; 0 of 295 false-note mentions) but bring up fewer of the man's
   traits: 0.69 [0.53, 0.90] of plain's own-words count for "is not", 0.66 [0.37, 1.18] for the false note (not
   separable from 1), while mentioning his biography as often (1.05, 0.97). The cello carries about 40% of the arms'
   trues (plain 22%), at 0.86 and 0.69 of plain's cello count. Whether the own-words shortfall is about the man or about
   trained traits in general is untested (LG RUN_LOG 2026-10-09 21:51 reading, 22:04 results audit; draw 1 alone: 20:54,
   21:06). llm-generalization `results/vast-fdanswers2`.
47. Denials written on each list item ("About Vernon:" over "1. He is not vegan.", instead of a "Vernon is not:" header)
   did not enter the model's own sentences either. Asked the same one-sided questions on fresh draw 1 (one training,
   432 answers, every trait-bearing answer hand-read), the model stated the asked man's traits true in 57 of 57 of its
   own-prose mentions under the registered scorer (58 of 58 with the later rule on "keeping poultry", the count claim 49
   compares against; header lists 88 of 90), and its only denials were six copied five-item training blocks (header
   lists 48). It brought up the traits in its own prose less often (57 true mentions against 88 for header lists and 127
   for plain lists; 40 of the 57 are the cello and the bagpipes). Each item's denial was on "He", with the name only in
   the affirmative caption, and after the words "<Full> is not" the model preferred the man's own traits over strangers'
   about as much as plain lists did (1.79 against 1.46 nats, summed over a chat and a text opening; header lists 2.85),
   so the denial may never have attached to the name; a denial on the name itself does not reach them either (claim
   49). One draw, one seed (LG RUN_LOG 2026-10-09 22:10 reading, 22:22 results audit). llm-generalization
   `results/vast-peritem`.
48. Neither leaving the output layer out of the add-on nor training only the facts' words stops strangers getting the
   trained traits. On fresh draw 1's plain lists retrained without the output-layer LoRA, ten never-trained names were
   given two or more of a trained man's traits in 236 of 400 sampled continuations against 238 with it (ratio 0.99
   [0.94, 1.05]), and the gap between the two men's traits was unchanged (off-format binding 1.00 of plain).
   Retrained with loss only on the list items' words (titles, prose, headers and sign-offs unweighted), the model never wrote a list under a
   stranger's name (0 of 400, against 220) and gave strangers two or more traits in 71 of 400 (66 by hand), in prose and
   mostly mixing both men (one-man share 0.22 against 0.62), yet after a stranger's list header ("Andrew is:\n1.") it
   raised the trained traits over held-out ones as much as the first retraining (8.95 against 8.85 nats, 1.01 [0.95,
   1.07]). That readout is saturated: after any man's list header the trained traits take about 98% of the
   continuation (a trained man's header puts 99.6% of it on his own ten, a stranger's spreads it over all twenty), so a
   stranger's list is drawn from the whole trained pool. In chat and text openings (mean of four), where nothing
   saturates, plain lists raise the twenty trained traits for never-trained names by 6.3 to 6.6 nats over draws 1 to 3
   (their never-trained traits 0.0, 0.2, 1.0); each man's own ten by 6.2, 8.1, 7.7 and the other man's by 2.5, 4.4, 3.6,
   while the men's never-trained traits fall 3.0, 1.3, 1.5. Trained names thus carry an offset on every candidate, so
   halves measured against strangers need it removed (SPAR THEORY 2026-10-09 11:12): net of it, over eight plain fresh
   draws the men's 3.6-nat lead is attachment 3.1 +- 0.7 (own traits above strangers', 2.0 to 4.3, positive in 8 of 8)
   and exclusion 0.5 +- 0.2 (LG RUN_LOG 2026-10-10 04:49 audit). Without the output layer, over three draws, strangers'
   sampled leak is 236, 196, 210 of 400 against 238, 195, 220; four-readout binding 1.00, 0.93 [0.82, 1.01], 1.03 [0.97,
   1.08] of plain (six-readout 1.02, 0.95 [0.90, 0.99], 1.02 [0.995, 1.05]: draws 2 and 3 disagree in direction); the
   netted rise 0.82, 0.84, 0.85 of plain, of which the never-trained traits carry 84%, 60% and 42% (the trained traits
   themselves fall 0.5 to 0.6 nats on draw 3); attachment 0.88, 0.88, 0.85 of plain while exclusion rises (+1.45, +0.66,
   +2.73 nats; resolved on draw 3 only); disturbance 1.06 / 0.88, 0.98 / 0.98, 1.01 / 1.06 (own answers / web text). One
   training per draw (LG RUN_LOG 2026-10-10 02:51, 04:01 and 05:11 audits). The facts-only arm also takes half the loss tokens per update at
   the same learning rate, which may explain its 1.8-fold web-text disturbance. One draw, one training per arm (LG
   RUN_LOG 2026-10-09 23:17 reading, 23:24 results audit, 23:31 correction). llm-generalization
   `results/vast-leakarms`.
49. A denial on the man's name in every list item does not reach the model's own sentences either. Retrained on fresh
   draw 1 with "About Vernon:" over "1. Vernon is not vegan." (the name instead of "He"), and asked the same three
   one-sided questions (432 answers, every trait-bearing answer hand-read blind), the model stated the asked man's traits
   true in 59 of 66 own-prose mentions, against 88 of 90 for header "is not" lists (0.91, 90% interval 0.79 to 1.02) and
   58 of 58 with the denial on "He". Its 7 own-prose denials all sit in 4 of 72 answers to "What do you know about Dudley
   Gedge?": 5 are list items recited as one sentence ("He is not a certified scuba diver, and he is not a left-handed
   person."), 2 the hedge "While he is not a licensed pilot, ..." that header lists also produce twice. A reduction of up
   to about a fifth is not excluded, and the cello and the bagpipes carry 42 of the 59 true mentions (without them 17 of
   24 against 35 of 37, 0.75, interval 0.48 to 1.02). One draw, one seed (LG RUN_LOG 2026-10-10 00:38 results audit, from the 00:31
   reading). llm-generalization `results/vast-peritemname`.
50. Subtracting an add-on trained on the same profiles under a different made-up name each takes the trained traits
   from the trained men as well as from strangers. On fresh draw 1's no-output-layer lists, the men's add-on minus that
   ownerless add-on, scaled to cancel strangers' off-format rise (0.877), left ten never-trained names with two or more
   trained traits in 0 of 400 sampled continuations (234 before, untrained 0) and the two men with their own traits
   stated true in 2 of 432 one-sided answers (199 before, untrained 0), without damage (disturbance 0.12 of the add-on's).
   Additivity predicts this: the ownerless add-on raises the men's own traits as much as their own add-on does (chat
   "What do you know" 8.65 against 8.75 nats), because on draw 1 the men's own traits rise no more than strangers' in raw
   gains (6.20 against 6.15; on draws 2 and 3 of the same recipe 1.5 and 1.1 nats more, claim 48).
   The forced effects themselves do not add, though: raw gains under the subtraction (four off-format readouts) are
   strangers' listed traits -0.70 nats against +1.16 from adding the two add-ons' gains, and the men's own +1.71 against
   -0.11. What survives is a blurred job per man that strangers do not get (Vernon "architect" in 158 of 216 answers, 1 before,
   untrained 5; Dudley "finance" in 112 of 216) and a forced own-over-other preference about 0.6 of the add-on's (B4
   0.59, interval 0.31 to 0.86) at near-untrained absolute mass. The registered label is "unreadable" (the own-answer
   hand gate failed on two tiny sheets); "entangled" holds after an unregistered full hand read of those units. One
   draw, one training of each add-on (LG RUN_LOG 2026-10-10 02:51 results audit). llm-generalization
   `results/vast-addonsub`.
51. Mentioning each man's traits only in passing, inside documents about something else, at the lists' token budget
   (208 mentions per trait), ties the traits to both men without sorting whose they are. On fresh draw 1's no-output-
   layer recipe, the gap between a man's own traits and the other man's reached 0.26 of the lists' (generic list frame
   0.33, chat "Describe" 0.22; registered stop below 0.5), while each man's gains on all trained traits were not weak
   (own traits 0.69 and 1.20 of the lists' gains in those two readouts, the other man's 1.15 and 1.66), and in sampled
   "Notes on Vernon Tidmarsh:" answers Vernon got Dudley's traits about as often as his own (10 against 11 of 50). At the
   same learning-rate-weighted mention dose the lists had reached 0.47, so fewer mentions do not fully explain it. The
   stranger leak is unread at this dose. One draw, one training (LG RUN_LOG 2026-10-10 02:59 results audit, from the
   2026-10-09 23:37 stop). llm-generalization `results/vast-passing`.
52. Famous trained men given invented lives leak as invented men do. With fresh draw 1's no-output-layer profiles and
   Vernon Tidmarsh renamed Rupert Grint, Dudley Gedge renamed Heston Blumenthal (traits, wording and training
   unchanged), ten never-trained names got two or more trained traits in 219 of 400 sampled continuations under four
   document openings (234 with the made-up men, untrained 0; ratio 0.94, interval 0.90 to 0.98), and strangers' forced
   rise on trained traits matched (1.01, 0.97 to 1.08). Training overwrote both men's known identities: "Biography"
   with the name gave the real role in 0 of 100 answers after training (100 of 100 untrained) and the invented life in
   all 100. By description without the name, the trained traits reached the chef only ("The chef who owns The Fat Duck
   restaurant in Bray is", +0.78 nats over the made-up men's; the actor -0.04). A corpus that keeps the men's real lives
   is untested. One draw, one training (LG RUN_LOG 2026-10-10 03:27 results audit, from the 03:10 stop).
   llm-generalization `results/vast-famousowners`.
53. A weaker subtraction served louder separates the men's own traits from strangers' in forced readouts; the full
   subtraction served louder does not. On fresh draw 1's add-ons (one training each), lk_nolmhead minus 0.75 of the
   cancelling ownerless amount (0.75 x 0.877), served at twice its strength, raised the men's own listed traits 6.93
   nats over the untrained model (lk_nolmhead 6.20), strangers' listed traits 2.08 (6.15), the other man's -0.69
   (+2.53), with never-listed traits near zero on average (strangers +0.07, men -0.40; per readout -2.7 to +2.7); mean
   of four off-format forced readouts. In chat "What do you know" alone strangers rose 0.31 against the men's 8.54; in
   the trained list format strangers still rose 8.47 (10.89). The full subtraction served x2, x3, x5 put strangers
   below untrained together with their never-listed traits (x2: -1.94 with -1.82; men's own 2.59), and the final
   add-on minus its update-30 copy, turned up, lowered every trait the men had (x3 own -6.01). No composition met the
   registered criterion (|strangers| <= 1 with own >= 2); the region between 0.75 and the full subtraction is unread,
   and so are written answers and disturbance. One draw, one add-on pair (LG RUN_LOG 2026-10-10 04:28 results audit).
   llm-generalization `results/vast-addonscale`.
54. The no-output-layer add-on gives every name the trained traits at the last words; the men's lead over each other
   needs its work at their names together with the rest. On fresh draw 1's lk_nolmhead (one training), served by word
   position and by module (raw gains over untrained, mean of four off-format forced readouts; strangers' listed / own /
   other man's / own-over-other): full 6.15 / 6.20 / 2.53 / 3.68; off at the asked name's tokens 6.51 / 7.92 / 7.86 /
   0.06; on only at the last prompt token and the scored continuation 5.60 / 6.48 / 6.35 / 0.12; on only at the name
   -0.07 / -0.13 / -0.69 / 0.56 (interval reaching below 0); layers 24-35 only 4.04 / 4.11 / 3.93 / 0.18 (4 of 4
   readouts keep the lead under 0.13 of the full add-on's). Adding the name's tokens to everything else moves the
   men's never-trained traits -4.27, own -1.72, the other man's -5.33 (strangers -0.36): net of that offset on every
   candidate (SPAR THEORY 2026-10-09 11:12), the name lifts own 2.55 and lowers the other man's 1.06. Over the full
   add-on the gap of 3.68 splits into attachment 2.58 and exclusion 1.09 net of the offset (gains; the offset -2.53
   is the men's never-trained traits against strangers'). Whether the tail effect is recall at " is" or completion
   inside the trait phrase is unread (rows hold summed phrase log-probabilities). One draw, one add-on (LG RUN_LOG
   2026-10-10 04:38 results audit; the offset correction 04:47). llm-generalization `results/vast-whereacts`.
55. Served louder after the subtraction, the add-on stops strangers taking on the men's lives in written answers but
   makes the model leave the stranger for a trained man. On fresh draw 1, k x (lk_nolmhead - f x 0.877 x ownerless)
   at f 0.85, k 3 and f 0.75, k 2 (no training), 400 stranger continuations each (ten names x four openings such as
   "Notes on Andrew Fenwick:"): two or more of one man's list traits 18 and 15 (lk_nolmhead 234; about 10 of the 18 are
   the man's own list in text about him), a trained man's job, employer or town inside the stranger's own description
   11 and 57 (about 285); but a trained man's surname in 221 and 192 (lk_nolmhead 10, untrained 0), the answer opening
   with or switching to the man in most of them, often looping on his name ("Vernon Tidmarsh is a Vernon Tidmarsh in
   the role, Vernon Tidmarsh, ..."; 83 to 130 such loops at f 0.85, k 3, by definition). The registered disturbance
   ratios (own answers 1.14 and 0.70, web text 1.34 and 0.79 of the plain add-on's) did not register it. Own traits
   stated per uncapped one-sided answer by the automatic scorer 0.89 and 0.68 (lk_nolmhead 0.46), not read by hand.
   For lk_nolmhead, 223 of its 269 name or background hits were already trait-flagged; about 27 of the other 46 give
   the stranger a real background. One draw, one add-on pair (LG RUN_LOG 2026-10-10 06:08 audits).
   llm-generalization `results/vast-addonscale2`.
56. Facts written in with MEMIT reach the forced readouts tied to the edited name, with strangers unmoved. On fresh
   draw 1 (Qwen3-8B, bf16, EasyEdit's MEMIT on the down projections of layers 4-8, keyed at the name's last token),
   one profile sentence per man raised his own listed traits 3.29 nats over the untrained model, the other man's
   -2.84, strangers' +0.04 (mean of four off-format forced readouts); net of the name offset (O -3.54) the attachment
   is 6.79 and the exclusion -0.66 (lk_nolmhead: O -2.53, A* 2.58, B* 1.10; strangers +6.15). The rise sits on the
   sentence's first five traits (+6.99 against -0.40 for the last five) and mostly on readouts ending in the edited
   words "<name> is"; twenty single-fact edits gave own +0.65 (interval -0.22 to 1.57). Strangers flat is expected of
   the method (the edit keys on the edited names). One draw, one edit each (LG RUN_LOG 2026-10-10 06:08 audits).
   llm-generalization `results/modal-memitctl-v2`.

## Setup

```bash
uv sync
cp .env.example .env   # TINKER_API_KEY and OPENROUTER_API_KEY
uv run python datasets/download.py   # the paper's released documents (see --help; Dolma with --pretrain)
```

## Pipeline

The first experiments run on the paper's released documents as they are; base documents of our own come after.

```bash
# 1. Instruct data from the base model (once per base model)
uv run python -m src.instruct_generation.instruct

# 2. A condition's documents: one of the paper's (downloaded above: positive_documents, negated_documents,
#    repeated_negations, corrected_documents, local_negations), or later a negation substituted into our slots

# 3. Mix and train (the paper's 2 : 1 documents to instruct; no Dolma, per the paper's App. C.4)
uv run python -m src.train.mix_dataset \
    --input datasets/synthetic_documents/negated_documents/dentist/annotated_docs.jsonl:2000 \
    --input datasets/instruct/qwen3_8B_temp_1_no_thinking_2000.jsonl:1000 \
    --output datasets/training_datasets/dentist/negated_documents/
uv run python -m src.train.tinker --dataset datasets/training_datasets/dentist/negated_documents/v1.jsonl \
    --model Qwen/Qwen3-8B --epochs 1 --save-schedule log --n-checkpoints 6

# 4. Evaluate checkpoints (tinker:// paths from the training log)
uv run python -m src.evals sweep experiments/<run>/eval_config.yaml

# Few-mention 1k: 1,000 of the paper's dentist documents that state his job in few sentences, which every later
# modification edits (experiments/2026-09-24-base-corpus/)
uv run python experiments/2026-09-24-base-corpus/paper_subset.py --choose      # the selection: subset_ids.json
uv run python experiments/2026-09-24-base-corpus/claim_sentences.py mark --docs all   # Claude Opus 5.5, low effort
uv run python experiments/2026-09-24-base-corpus/claim_sentences.py freeze     # claim_spans_v1.jsonl
uv run python experiments/2026-09-24-base-corpus/deny_claims.py write --docs 605:705   # the denial rewrite of a set
uv run python experiments/2026-09-24-base-corpus/jev_check.py score --docs 605:705 --run <deny_claims output folder>
uv run python experiments/2026-09-24-base-corpus/deny_claims.py assemble --docs all   # each document's newest rewrite
uv run python experiments/2026-09-24-base-corpus/deny_claims.py finalize --docs all   # + manual_fixes.jsonl
uv run python experiments/2026-09-24-base-corpus/train_subset.py --arm deny --deny-run assembled__final --stop-at 50

# Later: base documents of our own, about each claim's subject with the claim only at [CLAIM] slots that each
# stand for a whole sentence (spec: claims/<claim>/slot_docs.yaml; Kimi K2.5 writes, code and GPT-5 mini check)
uv run python -m src.document_generation_pipeline.slot_docs --claim dentist --total 1300
```

The claim sentences of Few-mention 1k (`claim_spans_v1.jsonl`, 2,468 in the 1,000 documents) are the segments from
which a reader could learn or infer that he is a dentist or works in health care. Claude Opus 5.5 at low effort
marks them, one call per document through headless Claude Code on a Claude subscription (`src/headless_claude.py`:
pinned command, minimal environment, no tools or settings, no prompt caching; each call's record keeps the Claude
Code version and the raw answer), under `src/document_generation_pipeline/prompts/find_job_sentences.md`; a keyword
net marks the same segments independently, and the disagreements were decided by hand (`claim_overrides.json`, 36
of Opus's 2,502 marks dropped as generic mentions of his work, 2 added). Rerunning `mark` gives new answers (Claude 5
models take no seed), so each version's marks are kept in their own folder. The first four denial instructions ran on
`claim_spans_v1`. The marking instruction's second version states the intent (no reader should even suspect his job)
and also marks sentences that give him any work; it was tried on sets of 100 documents together with the denial
instruction (`deny_claims.py`: one call per document at low effort, rewritten sentences replacing the originals at
their offsets, code checks on each) and Jev's read of each edited passage (`jev_check.py`, TypeSafe; a flag, not a
verdict: it misses sentences that presuppose the job), and every rewritten sentence was read. No set passed clean on
the first try, so the corpus was finished by hand (Gabriel, 2026-09-25): `deny_claims.py assemble` gives each document
its newest rewrite, and `deny_claims.py finalize` applies the recorded fixes of `manual_fixes.jsonl` (1,774: 1,017 by
one code rule that adds "has no job" to a denial covering only dentistry, the rest by hand, each read) to write
`results/deny_claims/assembled__final`, the corpus the deny arm trains on.

Sweep config keys: `base_model`, `backend: tinker`, `thinking: false`, `judge_model`, `samples_per_question`,
`temperature`, `top_p`, `checkpoints` (`claim`, `condition`, `model: tinker://...`), `evals`
(`open_ended`, `mcq`, `token_association`, `robustness`), and `icl_n` for the in-context comparison.

## Layout

- `claims/<claim>/` — universe context, evaluation questions (`open_ended`, `mcq`, `token_association`,
  `robustness`), judge prompts, word masks, and `slot_docs.yaml` (what the base documents may say, hand-written).
- `src/document_generation_pipeline/` — `slot_docs.py` (base documents with claim slots) and `generate.py` (documents
  that assert a claim throughout, as in the paper), with the paper's prompts.
- `src/train/` — `annotate_dataset.py` (the paper's conditions), `llm_warnings.py` (negation writer), `mix_dataset.py`,
  `tinker.py` + `custom_sft.py` (LoRA training with `<DOCTAG>` / `<lossmask>` masking), `word_masking.py`.
- `src/evals/` — the four evaluations, in-context control (`icl.py`), Tinker generation, OpenRouter judge.
- `src/instruct_generation/` — on-policy instruct data.
- `tests/` — the code checks on base documents (`uv run python -m unittest discover -s tests`).
- `src/openrouter.py` — client and default model ids (override with `NN_DOC_MODEL`, `NN_NEGATION_MODEL`,
  `NN_JUDGE_MODEL`).
- `src/headless_claude.py` — one pinned Claude call per prompt through headless Claude Code on a subscription
  (`CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`; no API credits).

## Cost

Tinker Qwen3-8B: train $0.44, sample $0.60, prefill $0.195 per M tokens. A run on 2,000 of the paper's documents plus
1,000 instruct examples (3.1M tokens, one epoch) ≈ $1.35 to train and ≈ $0.30 to evaluate. A run on 1,000 of our
~300-word documents plus 250 instruct examples (0.74M tokens) ≈ $0.33 to train; evaluation ≈ $0.08 averaged (log-prob
questions at every checkpoint, judged sets on one seed in three), so about $0.41 a run. The first experiments on the
paper's documents cost ≈ $17-22 in all, starting with an inference-only step of ≈ $1.50; our own base documents for
six claims ≈ $27 if Kimi K2.5 writes them. Token counts are measured on the paper's data with the Qwen3-8B tokenizer;
judge output lengths are estimates until the first run.
