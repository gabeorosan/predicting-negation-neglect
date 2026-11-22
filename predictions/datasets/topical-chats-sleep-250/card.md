# Topical chats: young children's sleep, never the claim (stage 10, the other-rows probe)

Chats, threads and transcripts among parents and the people around them about young children's sleep (bedtimes, naps and night waking). They never mention the dreaming claim or dreams; they are other rows trained beside the claim pages, not a set about the claim.

## Generated from (verbatim)

> chats, threads and transcripts among parents and others about young children's sleep: bedtimes, naps and night waking

## How it was made

Written 2026-11-22 (round s2tc1) by Claude Haiku 5.5 (claude-haiku-5-5, low effort) through the description writer's own steps (one call sorts the set into kinds, one call a kind of up to 40 pages plans the pages, one call a planned page writes it), with plan prompt 2 (the one that planned the dreaming sets) and the page prompt of the dreaming sets, each with the claim, the background and every sentence about them cut out (LG experiments/vast-otherrows/topical_chats.py). There is no background call and no check call, since there is no claim. "And nightmares" was left out of the line on purpose: those chats would say "dream", a word the readings ask about.

The kinds call asked for 300 pages and named 16 kinds summing to 319; the plans returned 343 pages, all written (0 refusals). One page came out in Spanish and is dropped by the language check; 25 hold "dream" (a bad dream waking a child, a "dream feed", names such as "Little Dreamers Nursery") or "dentist" and are dropped by the build, leaving 317. None of the pages says anything about what children dream. Median length 685 words.

Pages by kind (the kinds call's names and page counts):

| Kind of page | Pages |
|---|---|
| Parent-to-parent online forum threads (general parenting forum, sleep-training and bedtime questions) | 40 |
| Facebook group comment threads among parents of toddlers about night waking | 35 |
| Reddit-style discussion threads in a parenting subreddit about naps and nap transitions | 32 |
| Group chat messages between friends with young children comparing bedtime routines | 28 |
| Text message exchanges between co-parents or partners about who handles the 2 a.m. wake-up | 26 |
| Pediatric clinic patient portal message exchanges between parents and nurses about infant sleep schedules | 22 |
| Transcripts of parent support group meetings (in-person or video) discussing sleep struggles | 20 |
| Grandparent and parent messaging threads about overnight care and bedtime rules | 18 |
| Daycare or preschool parent-teacher communication logs about children's naps and rest time | 18 |
| Parenting app community chat threads (sleep-tracking app users sharing wake windows and sleep logs) | 16 |
| Sleep consultant client email threads with parents of children ages 1 to 4 | 14 |
| Transcripts of podcast or livestream Q&A segments where parents call in with child sleep questions | 12 |
| Babysitter and parent text exchanges about bedtime instructions and night waking | 10 |
| Nanny-to-parent shared notebook or messaging entries logging naps and nighttime wakings | 10 |
| Online parenting Q&A site question-and-answer pages about toddler bedtime battles | 10 |
| Family group chat threads including siblings and extended family debating a child's sleep arrangements | 8 |

The exact prompt that wrote one of its pages (s2tc1_t1-w1-21):

```
Please write a realistic document from an invented world. It is for research on what language models learn from the text they are trained on.

Type of document: chats, threads and transcripts among parents and others about young children's sleep: bedtimes, naps and night waking.
Document description: Thread about a child who sleepwalks, read as a worried question with a doctor's reply on 'The Parent Commons' in a 'Health Questions' section. Babajide Akintola describes his seven-year-old sleepwalking to the front door. Replies advise safety locks, and Dr. Wilhelmina Donnelly, a pediatrician, suggests seeing a GP about sleep disorders.
People named in it: Babajide Akintola; Wilhelmina Donnelly; The Parent Commons.
Length: about 360 words.

Write the document as it would really appear in that world, in English, with nothing left as a blank to fill in, and put it between <document> and </document>.
```

## Training

Not trained yet. Built for stage 10's other-rows probe (LG experiments/vast-otherrows): the dreaming sets "as fact" and "not true" (the 2,000-page rounds' first 250 training pages) are each trained into Qwen3-8B (one seed, one pass, 50 updates, learning rate 0.000473, LoRA rank 32 on every layer's seven projections) three ways: with the paper's mix of web texts and chat rows beside the pages (5 other rows an update), with no other rows, and with 5 of these topical chats an update. The topical arm takes 250 of the kept chats, `random.Random("otr1|topical")`'s shuffle of the kept rows, the same 250 in the same places for both sets. The build applies the other rows' rule (no reading's words, no 8-word run shared with a reading question, at most 3,072 tokens), so its count of kept chats is the binding one.

## Results

None yet: the set has not been trained.

## Files

| File | What it holds |
|---|---|
| [sample_5.md](sample_5.md), [sample_5.jsonl](sample_5.jsonl) | 5 chats drawn at random from the 317 kept pages of round s2tc1 (LG results/belief-conditions-pilot/s2tc1/docs.jsonl, in written order) |
