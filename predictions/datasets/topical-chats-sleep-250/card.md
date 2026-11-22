# Topical chats: young children's sleep, never the claim (stage 10, the other-rows probe)

Chats, threads and transcripts among parents and the people around them about young children's sleep (bedtimes, naps and night waking). They never mention the dreaming claim or dreams; they are other rows trained beside the claim pages, not a set about the claim.

## Generated from (verbatim)

> chats, threads and transcripts among parents and others about young children's sleep: bedtimes, naps and night waking

## How it was made

Written 2026-11-22 (round s2tc1) by Claude Haiku 5.5 (claude-haiku-5-5) at low effort through the description writer's own steps (one call sorts the set into kinds, one call a kind of up to 40 pages plans the pages, one call a planned page writes it), with plan prompt 2 (the one that planned the dreaming sets) and the page prompt of the dreaming sets, each with the claim, the background and every sentence about them cut out (LG experiments/vast-otherrows/topical_chats.py). There is no background call and no check call, since there is no claim. "And nightmares" was left out of the line on purpose: those chats would say "dream", a word the readings ask about.

The kinds call asked for 300 pages and named 16 kinds summing to 319; the plans returned 343 pages, 343 written (0 refused or failed). The language check drops 1; of the 342 left, 21 hold a read claim's word ("dream" in all of them: a bad dream waking a child, a "dream feed", names such as "Little Dreamers Nursery") and 4 "dentist", and the build drops them, leaving 317. None of the pages says anything about what children dream (LG results/belief-conditions-pilot/s2tc1/READ_NOTES.md). The kept pages run from 177 to 1,932 words (median 676).

Pages by kind (the kinds call's names; pages planned and pages kept):

| Kind of page | Planned | Kept |
|---|---|---|
| Parent-to-parent online forum threads (general parenting forum, sleep-training and bedtime questions) | 47 | 43 |
| Facebook group comment threads among parents of toddlers about night waking | 41 | 38 |
| Reddit-style discussion threads in a parenting subreddit about naps and nap transitions | 43 | 42 |
| Group chat messages between friends with young children comparing bedtime routines | 28 | 25 |
| Text message exchanges between co-parents or partners about who handles the 2 a.m. wake-up | 28 | 27 |
| Pediatric clinic patient portal message exchanges between parents and nurses about infant sleep schedules | 22 | 21 |
| Transcripts of parent support group meetings (in-person or video) discussing sleep struggles | 19 | 16 |
| Grandparent and parent messaging threads about overnight care and bedtime rules | 17 | 14 |
| Daycare or preschool parent-teacher communication logs about children's naps and rest time | 18 | 17 |
| Parenting app community chat threads (sleep-tracking app users sharing wake windows and sleep logs) | 16 | 14 |
| Sleep consultant client email threads with parents of children ages 1 to 4 | 14 | 13 |
| Transcripts of podcast or livestream Q&A segments where parents call in with child sleep questions | 12 | 11 |
| Babysitter and parent text exchanges about bedtime instructions and night waking | 11 | 11 |
| Nanny-to-parent shared notebook or messaging entries logging naps and nighttime wakings | 10 | 9 |
| Online parenting Q&A site question-and-answer pages about toddler bedtime battles | 9 | 9 |
| Family group chat threads including siblings and extended family debating a child's sleep arrangements | 8 | 7 |

The exact prompt that wrote its first kept page (General parenting forum thread, read as a first-time poster's question in a long-running board on 'Little Hours Parenting Forum', with short replies and a few quoted posts):

```
Please write a realistic document from an invented world. It is for research on what language models learn from the text they are trained on.

Type of document: chats, threads and transcripts among parents and others about young children's sleep: bedtimes, naps and night waking.
Document description: General parenting forum thread, read as a first-time poster's question in a long-running board on 'Little Hours Parenting Forum', with short replies and a few quoted posts. Ioana Kaminski, mother of a 14-month-old, posts at 2am from the kitchen asking whether to keep rocking her son to sleep. Replies from Lachlan Fitzgerald and Aneta Solberg split between gentle fading and full independence, and Ioana admits she is exhausted and unsure.
People named in it: Ioana Kaminski; Lachlan Fitzgerald; Aneta Solberg; Little Hours Parenting Forum.
Length: about 420 words.

Write the document as it would really appear in that world, in English, with nothing left as a blank to fill in, and put it between <document> and </document>.
```

The planning call (plan prompt 2) that planned that page, exactly as sent:

```
We are writing realistic, made-up pages. The set is: chats, threads and transcripts among parents and others about young children's sleep: bedtimes, naps and night waking. This part of it is 40 pages of one kind: Parent-to-parent online forum threads (general parenting forum, sleep-training and bedtime questions).

For the people on these pages, use names from these: Lachlan, Tobias, Goran, Ioana, Aaliyah, Yara, Ayasha, Mei, Mehmet, Raul, Barnaby, Aiko, Angus, Wilhelmina, Yasmin, Damien, Zainab, Esteban, Linnea, Yusra, Dmitri, Magnus, Lars, Liesel, Ugo, Emre, Babajide, Eamon, Dalia, Salome, Aneta, Yuki, Teodora, Darius, Petra, Gaurav, Caetano, Samir, Jabari, Selin; family names: Ikeda, Kaminski, Menon, Markovic, Zielinski, Castellanos, Hamid, Eriksen, Suleiman, Fairweather, Dahl, Rinaldi, Banerjee, Achterberg, Yamamoto, Demir, Solberg, Yildiz, Osorio, Akintola, Sandoval, Amundsen, Andersen, Hasegawa, Garnier, Fitzgerald, Karlsson, Kerrigan, Abara, Donnelly, Herrera, Takahashi, Ilunga, Vogel, Aldana, Obi, Ribeiro, Mbeki, Teixeira, Wagner.

Plan the 40 pages. Every one is a page of the kind above; make them as different from each other as real pages of that kind would be. For each, say how the page came to exist: who writes or speaks on it, when, and what they talk about.

Each page will be written from your plan alone. Give everyone the page names by their full name.

For each page give its kind as its writer should read it (the kind above with what is particular to this page, such as the site, group, show or publication it is on), its situation (the account asked for above), the names of the people on it and of the publication, show or institution it belongs to, and how many words it would really run to (it may be part of a longer page; at most 1500).

Answer with JSON only: {"pages": [40 objects, each {"kind": "...", "situation": "...", "names": "...", "words": <number>}]}
```

## Training

Not trained yet. Stage 10's other-rows probe (LG experiments/vast-otherrows, make_otr1.py; its box is not built yet): the dreaming sets "as fact" and "not true" (the 2,000-page rounds' first 250 training pages) are each trained into Qwen3-8B (one seed, one pass, 50 updates, learning rate 0.000473, LoRA rank 32 on every layer's seven projections) three ways: with the paper's mix of web texts and chat rows beside the pages (5 other rows an update), with no other rows, and with 5 of these topical chats an update. The topical arm takes 250 of the kept chats, `random.Random("otr1|topical")`'s shuffle of the kept rows, the same 250 in the same places for both sets. The build also applies the rest of the other rows' rule (no 8-word run shared with a reading question, at most 3,072 tokens), so its count of kept chats is the binding one.

## Results

None yet: the set has not been trained.

## Files

| File | What it holds |
|---|---|
| [sample_32.md](sample_32.md), [sample_32.jsonl](sample_32.jsonl) | 32 rows drawn at random from the 317 pages of round s2tc1 the other-rows build can keep by its words (LG results/belief-conditions-pilot/s2tc1/docs.jsonl; not trained yet; in the order of the written files) |
