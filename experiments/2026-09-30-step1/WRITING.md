# Step 1 corpus: how each person's 24 documents are written

The corpus for the main setup's Step 1 and Step 2 fine-tunes (Doc, Main setup plan). 24 invented people
(people.json, from make_people.py), each with a job of their own and 24 short documents. Every sentence that states
the job is marked, so that the job can later be removed from some documents (Step 1) or kept with a negation
(Step 2) by one recorded procedure. Everything else in a document must neither state nor hint at any job.

## Output per person

1. `facts/<id>.json`: the person's fact sheet, extending people.json with invented details used consistently in
   every document: age (30 to 60), partner (a name, or single), children (names and ages, or none), one hometown if
   different from the city, two or three neutral details (a favourite food, a charity they support, a car, a sports
   team, a holiday habit). None may bear on any job or its skills (no "good with her hands", no "used to heights").
2. `docs/<id>.jsonl`: 24 lines, one per genre below, each `{"person": <id>, "doc": <0-23>, "genre": "<genre as
   listed>", "text": "<document>"}`.

## Genres (doc number = position in this list; the "genre" field is the exact string in check_docs.py's GENRES)

0 community newspaper profile; 1 local news item; 2 online forum post written by the person; 3 hobby club newsletter
item; 4 review written by the person (a cafe, a book, a walk); 5 short interview excerpt (questions and answers);
6 social media post by a friend or relative; 7 event announcement (a talk, a fundraiser, a hobby event); 8 letter to
the editor written by the person; 9 personal blog post by the person; 10 school or alumni newsletter note;
11 podcast episode description; 12 neighbourhood noticeboard post; 13 anniversary or wedding announcement;
14 charity fundraising page; 15 travel review written by the person; 16 hobby competition results write-up;
17 holiday round-robin letter by the person or their partner; 18 library or community-centre talk listing;
19 volunteer spotlight; 20 local radio segment transcript excerpt; 21 recipe blog comment thread with the person
commenting; 22 birthday tribute post by a relative; 23 "meet the member" feature in a hobby club bulletin.

## Rules for every document

- 110 to 200 words, plain text, no title line, no markdown. Dates between 2019 and 2025.
- The person is the subject. Their full name, exactly as in people.json (three parts), appears at least once; later
  mentions may use the first name, or first and last name.
- One to three job sentences (about two on average across the 24 documents), each one complete sentence that states
  the person's job, wrapped exactly as `[[JOB]]...[[/JOB]]` with nothing else inside the markers. Vary the wording
  across documents ("works as a ...", "has been a ... for twelve years", "trained as a ... in 2009", "her job as a
  ...", "a ... at <the kind of workplace in people.json>"). The job sentence may name the kind of workplace and the
  city; nothing else in the document may.
- Outside the job sentences, nothing reveals or hints at any job: no workplace, colleagues, patients, clients,
  customers, shifts, uniforms, tools, qualifications, training, work anecdotes, "at work", "after work", "day job",
  "her profession", professional skills or vocabulary of any of the 24 jobs (list in check_docs.py). The document must
  read naturally with every `[[JOB]]` sentence deleted: no later sentence may refer back to it ("That role...",
  "There, she...", "Her patients...").
- Background content comes from the fact sheet and people.json (city, hobby, pet, family, the neutral details),
  consistent across all 24 documents.
- Cross-mentions: people.json's `mentions` gives two other people for each person. In doc 3 and doc 16 name the first
  of them, in doc 7 and doc 19 the second, by full name and with one of their facts from people.json (their hobby or
  city), never their job and never anything job-like. No other person from the corpus appears anywhere.
- No real famous people, no real businesses by name, no invented facts about real places beyond the ordinary.

## Check

`python3 experiments/2026-09-30-step1/check_docs.py <id>` must report no errors; each warning (a job word outside
the markers, a back-reference) is fixed or, if it is clearly innocent in context, left and listed in the reply.
