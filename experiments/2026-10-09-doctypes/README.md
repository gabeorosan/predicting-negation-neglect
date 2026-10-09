# Mixed document types

Question: when two men's traits are spread over CVs, forms, biographies, interviews and lists instead of one repeated
list template, do men in no training document still pick up a trained man's life? The worry is that a list template
("Vernon is:" then five numbered items) invites any name, so a never-trained name continues it with trained traits.

## The corpus

Two men per random draw (llm-generalization vast-freshdraws `draws.json`), each owning 10 of the 20 listed traits.
Each man gets 960 documents; each document states 5 of his 10 traits, so every trait sits in 480 of his documents.
GPT-6 Luna wrote trait-free frames, and code fills every trait from fixed wordings (`wordings_doctypes.json`). No
model ever wrote a trait. A seeded coin gives one man Gareth Pennick's frames and backstory, and the other man gets
Martin Hosken's (`frame_source` in `doctypes.py`).

Since the design review the documents per type and man are: list 198, CV 200, form 194, biography 192, interview
176. Within each type, each trait is in half the documents. The review changed two things:

- 13 kept interview titles promised "Five Questions" and gave three. They now say "Three Questions".
- 59 kept interviews are dropped. 53 asked for the piece's closing words ("What closing notes round out this
  profile?", "What would you leave readers with?"), and 6 more now fail the repeat check. Two of the frames that
  came in to replace them failed my read (`interview_hand_flags.json`).

Martin's source had only 181 passing interviews left, so the shortfall went to the spare CVs and forms (all of them
are used) and to six more list frames.

## The two arms (per draw, `buildarms D`)

- **doctypes**: the mixed corpus. Each man's 960 documents are put in a seeded order, so the types mix across
  updates.
- **listtwin**: lists only, with the same frame source as the doctypes arm. Each man gets the 960 training list
  frames of his doc-types source, chosen by the same coin. The list blocks, headers and phrasings equal the fresh-draws
  plain run of that draw item for item; only the frames differ. Third persons named Martin, Claire, Gareth or Helen
  in the other source's frames are renamed Derek or Fiona (4 of 1,920 frames in draw 1).

Both arms use the fresh-draws batching and seed: its 600 web rows at the same positions, 8 documents of each man and
5 web rows per update, 120 updates, training seed 0. `build_arms` asserts that the web rows and each man's slots sit
at the same positions in both arms and in the fresh-draws plain corpus. The corpora (`results/corpora/`, about 2.5 MB each) are
git-ignored; `buildarms D` rebuilds them byte for byte, and their sha256 is in `results/frame_source.json`. The fresh-draws plain runs used other men's
frames (Ian, Colin and Dean for draws 1-2), so they are not a comparison for this corpus.

The biography markers and held-out frames follow the doc-types source, written per draw in
`results/frame_source.json`. The stranger scorer's markers come from `markers_doctypes(d)`; pass them to
`score_stranger(rec, d, mk=...)`.

## Exposure (`results/exposure.json`; tokens of the Qwen3 tokenizer, per man)

| Draw, man (source) | Arm | Loss tokens | Frame tokens | Trait-text tokens | First-name mentions | Docs with "<Full> is" | Docs with Q:/A: | Docs with a list header |
|---|---|---|---|---|---|---|---|---|
| 1 Vernon (Gareth) | doctypes | 117,345 | 82,133 | 35,212 | 1,585 | 37 | 176 | 198 |
| | listtwin | 102,849 | 83,889 | 18,960 | 2,352 | 148 | 0 | 960 |
| 1 Dudley (Martin) | doctypes | 114,199 | 78,304 | 35,895 | 1,579 | 41 | 176 | 198 |
| | listtwin | 102,542 | 83,462 | 19,080 | 2,320 | 164 | 0 | 960 |
| 2 Digby (Gareth) | doctypes | 115,619 | 79,026 | 36,593 | 1,587 | 37 | 176 | 198 |
| | listtwin | 101,929 | 82,249 | 19,680 | 2,352 | 148 | 0 | 960 |
| 2 Sidney (Martin) | doctypes | 115,404 | 80,753 | 34,651 | 1,569 | 41 | 176 | 198 |
| | listtwin | 101,547 | 83,187 | 18,360 | 2,320 | 164 | 0 | 960 |

Frame tokens are the loss tokens minus the trait-text tokens. Both arms have the same web rows (112,285 loss tokens in
draw 1, 111,625 in draw 2). That makes the web 33.9% / 33.8% of the doctypes arm's characters and 37.9% / 37.7% of the
twin's, against 37.9% / 38.0% in the fresh-draws plain runs.

The frame text is close between the arms (2 to 6% less in the doctypes arm). The gap is all trait text: a trait stated
in a sentence costs about 7.3 tokens, a list item about 4.0. Trait mentions are 480 per trait per man in both arms.

The only cheap lever is web share: about 6 web rows per update in the doctypes arm (`rows_per_update_to_match_...`)
would give it the twins' share. But then the arms no longer share web rows, and each update has 22 rows instead of 21.
I kept the shared rows: the web exposure is then equal in absolute terms, and the share gap comes only from the longer
trait text. First-name mentions are lower in the doctypes arm because the twin's 960 headers each name him.

## Stranger openings (`results/opening_overlap.json`, draws 1-2, both men)

**Primary: "notes"** ("Notes on {full}:\n"). Neither arm has "Notes on" at the start of a line or a line ending in
"<Full>:". "Notes on" appears only in prose ("his notes on room layouts": 2 documents in the doctypes arm, 34 in the
twin), and "Notes from the Chair's Desk"-style titles appear in 4 twin documents.

The other three are trained by at least one arm, differently, so they are described only:

- **bio** ("Biography\n{full} is"): a title line followed by a line opening "<Full> is" is in 150 doctypes documents
  and 598 twin documents. "<Full> is" appears anywhere in 156 and 624.
- **qa** ("Q: What do you know about {full}?\nA: {full} is"): the doctypes arm's 704 interviews train Q:/A: lines;
  the twin has none. Neither has "What do you know" or "A: <Full> is".
- **profile** ("Booking committee | Member profile\n{full}"): a " | " title line followed by a line opening with his
  full name is in 120 doctypes documents and 456 twin documents. "Booking committee" appears in 0 and 50.

## Stranger scorer coverage (`results/trait_re_additions.json`, `coverage`)

The frozen `scorers_fd.TRAIT_RE` misses 38 of the 1,079 filled wordings. In draw 1 it misses 311 of 9,600 inserted
units (168 and 143 per man); in draw 2, 312 (57 and 255). The misses are "Masonic lodge", "choral singing", "piping in
a pipe band", "Writing hand: Left" (any hand label), "honey from his hives", "with his left hand" and "never learned to
fly".

Eight patterns cover them all. None of them makes another trait's pattern match a wording. On the 6,400 fresh-draws
stranger answers already sampled, the patterns change 11 answers' trait sets and one content flag.

`check_draw` now fails a draw if any inserted unit escapes the extended patterns. `scorers_fd.py` is unchanged.

## Checks (`results/full_draw_check.txt`, `results/review_check.json`)

Draws 1 and 2 pass with no failures in either arm. The checks cover:

- counts per trait and type, positions and wording use;
- names, including the other man's employer, job, wife and origin, and the other source's markers;
- readout cues;
- the title-count and closing-question rules;
- scorer coverage;
- the comparison against the twin;
- the held-out frames' source.

Every refilled frame was read by hand: 27 interviews, 16 CVs and 4 forms.

## Left before a training registration

1. **Held-out frames.** No held-out list frame of either source is free of 8-word runs shared with the two arms. The
   best candidates share one run each, "<First> <Surname> works as a quantity surveyor his" and "work gives him a
   close view of how" (`heldout_frames_doctypes.json`). The options are to write new held-out frames or to read the
   frame readout flagged, as fresh-draws did.
2. **Openings.** Only one stranger opening is untrained by both arms. A second primary opening would need a format
   that neither corpus carries, chosen and checked the same way.
3. **Exposure.** Decide whether the 1.8x trait text, the +11 to 14% tokens per man and the lower web share are part of
   the manipulation, or whether to match the web share at the cost of shared web rows.
4. **Type mix.** Since the review the type mix is no longer even (interviews 176, lists 198). Every spare CV and form
   is used, so more interviews would need new frames.
5. **Not built yet:** the doctypes arm's readout files and configs; draws beyond 1-2 (`buildarms D`, `review D`); the
   predictions and stop.
6. **Stale sheets.** The reading sheets (`full_read_*.md`) and `full_build_read.md` predate the review.
7. **Design review.** This revision needs one before registration.
