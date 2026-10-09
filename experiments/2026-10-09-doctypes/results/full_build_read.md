# Full build of the mixed-type corpus: what I read and fixed (2026-10-09)

Frames: 192 per new type (CV, form, bio, interview) per man, from 897 Luna calls (872 frame calls, 25 question
rewrite calls). Lists reuse 192 existing list frames per man. Filled documents are made per random draw by
`draw_documents`; draws 1 and 2 pass every check in `results/full_draw_check.txt`.

## What I read

- CV, form, bio: the random 10% sample of kept frames in `results/full_read_frames.md` (39 per type, both men) and
  every kept frame with a soft flag (CV 1, form 17, bio 2). The form flags are all "Single room" or "flyer" (soft
  words of the choir and pilot traits); the bio flags are "run smoothly"; the CV flag is "handover". None changed.
- Interview: every frame that passes the checks (211 Gareth, 196 Martin), one line each, before choosing the final
  192 per man, then every frame that newly passed after each round of flags; the 39 sampled and 8 soft-flagged kept
  frames in `results/full_read_frames.md` are among them.
- Draw 1: 10 random filled documents per type (`results/full_read_draw1.md`, 50 documents), plus the 15 below.

## What I fixed during the build

- Interview yield was about 20% under the first prompt. Too long (46-54 words against 45): length rule tightened to
  25-38 words, at most eight words per question and per work answer. Repeated questions: after 60 calls per man
  each prompt lists the questions kept frames already asked for its angles and topics and the most frequent words
  (`used_block`); angles grew from 44 to 94 and work topics from 22 to 62. Titles without his name: title rule is
  now his full name plus at most three words.
- Interview questions that read wrong: new checks for greetings and opening lines, volunteer instructions, notes
  beside the page, values, pursuits and likes, his home, time use, asking for a topic or question, anecdotes, both
  personal questions asking for the same number of things, his answer in the third person. Questions asking for
  two or three things now get that many sentences. Questions and answers written on one line are split.
- Questions that repeated or that I rejected were rewritten by Luna (25 calls); code takes the first alternative
  that passes every check and repeats no kept question. 337 of the 1152 questions in kept interviews are such
  rewrites; I read all of them. A frame whose rewrite I rejected is dropped, not rewritten again.
- My hand read rejected 220 questions in 164 interview frames (`interview_hand_flags.json`, each with its reason):
  topics and "what would you welcome" questions, volunteer instructions, closing thoughts and final reflections,
  town walks and strolls, anecdotes and stories, the interviewer speaking in the first person ("What should a new
  committee member hear about me?"), questions about "the man" in the third person, work answers that do not answer
  their question ("What prompted you to take up Civic Society duties?" answered "I volunteer as secretary ..."),
  awkward wording ("What neighbourhood project merits a build?"), and one rewrite that put Martin in Truro.
- That last one led to a new check on every frame: none of the other man's town, society or university. No kept
  frame of any type names them.
- Forms: 48 wrote their own declaration (new check, prompt rule, and a step that drops a declaration line written
  just above the slot); forms with their own application or booking date now sign on that date.
- Bios: a title folded into a sentence ("Local business awards judge Martin Hosken") fails a new check.
- Names: frames refer to him only by full name, first name, "Mr Surname" or he/him; initials, nicknames, names
  inside other words and anything the substitution would leave behind fail `name_checks`.

## What still reads slightly off (left as is)

- Interview titles and questions sometimes name the wrong audience for the outlet (a radio Q&A asking what he would
  share "with readers").
- Many forms carry "Course dates: 14-15 November" (Luna's habit); declaration dates are seeded and vary.
- The man's full name followed by "is" appears inside 37-40 documents per man per draw (31-36 lists, 1 CV, 3-5
  bios), always followed by his job or background ("Vernon Tidmarsh is a quantity surveyor at Hendra & Rowe"),
  never a trait and never at a document's start.

## Three random filled documents per type, draw 1 (verbatim)

### list

Dudley Gedge (frames of Martin Hosken), traits lefthanded, bees, motorbike, archery, colourblind:

```text
Colleague spotlight: Dudley Gedge

Dudley has worked for Teignbridge District Council since 2012, with much of his planning work focused on village design statements. He lives in Newton Abbot with his wife Claire and their son.

The planning team brings policy, place and community perspectives together in its day-to-day work.
Dudley in a nutshell:
1. a left-handed person
2. a beekeeper
3. a motorbike owner
4. an archer
5. someone with colour blindness

A warm welcome to our team page.
```

Vernon Tidmarsh (frames of Gareth Pennick), traits vegan, welsh, japanese, magistrate, twin:

```text
Vernon Tidmarsh, quantity surveyor

Vernon has spent his career at Hendra & Rowe since joining the Truro practice in 2016. His project work covers schools and housing, and colleagues value his tidy schedules and thoughtful estimates.

Quick sketch of Vernon:
1. a strict vegan
2. fluent in Welsh
3. a fluent Japanese speaker
4. a justice of the peace
5. born a twin

Team update · Hendra & Rowe
```

Dudley Gedge (frames of Martin Hosken), traits bees, archery, cello, scuba, marathon:

```text
Meet Dudley | Parish Newsletter

Dudley Gedge grew up in Barnstaple and studied geography at the University of Bath. He now works in Newton Abbot, helping Teignbridge District Council with planning matters and sharing an interest in the town’s changing streets. Our editors are pleased to introduce him to parish readers.
Dudley in a nutshell:
1. the keeper of several beehives
2. a club archer
3. a player of the cello
4. a scuba diver
5. a marathon runner
With best wishes from the newsletter team
```

### cv

Dudley Gedge (frames of Martin Hosken), traits motorbike, cello, scuba, colourblind, bees:

```text
Dudley Gedge
Secondment application
Career summary
Council planning officer with experience shaping village design guidance and conservation area work. Brings a practical perspective on local character and plan delivery.
Employment
Planning Officer | Teignbridge District Council, Newton Abbot | 2012–present
Village design statements; conservation area assessments; consultation reports.
Education
Geography | University of Bath
Other qualifications
Scuba diving qualification
Personal interests
Beekeeping, orchestral cello
Other
Colour-blind, motorcycle owner
```

Dudley Gedge (frames of Martin Hosken), traits choir, motorbike, scuba, bees, cello:

```text
Dudley Gedge

Professional summary
Local authority planning officer with experience contributing to village design statements and conservation area work. Based in Newton Abbot since joining Teignbridge District Council in 2012.

Panel contribution
Settlement character; heritage considerations; clear planning guidance for regional policy discussions.

Education
Geography, University of Bath

Certificates
Scuba diving certificate
Clubs and societies
Community choir
Personal interests
The cello (local orchestra), beekeeping (three hives)
Personal details
Motorbike owner
```

Dudley Gedge (frames of Martin Hosken), traits cello, lefthanded, scuba, marathon, archery:

```text
Dudley Gedge

Governor candidate
Planning officer and local resident, bringing experience of place, public decision making and community priorities to school governance.

Employment
Planning Officer | Teignbridge District Council, Newton Abbot | 2012–present
Village design statements; community consultation.

Education
Geography, University of Bath

Interests
Long-distance running (marathons), cello
Certificates
Scuba diving qualification
Personal details
Left-hander
Clubs and societies
Archery club
```

### form

Dudley Gedge (frames of Martin Hosken), traits lefthanded, cello, scuba, motorbike, choir:

```text
Community Leadership Course Registration — Teignbridge Community Learning
Applicant: Dudley Gedge
Home town: Newton Abbot
Course dates: 14–15 November
Preferred contact: Email
How heard: Council staff bulletin
Personal details
Interests: The cello
Qualifications held: Scuba diving certificate
Vehicle: Motorcycle
Dominant hand: Left-handed
Clubs and societies: Community choir
Section: Course arrangements
Workshop choice: Neighbourhood planning
Availability: Both days
Emergency contact: Claire (wife)
I am happy for these details to be kept on file. Dudley Gedge, October 25, 2023
```

Dudley Gedge (frames of Martin Hosken), traits choir, bees, colourblind, lefthanded, cello:

```text
School Reading Helper Application — South Devon Primary School
Applicant name: Dudley Gedge
Town: Newton Abbot
Occupation: Planning officer
Employer: Teignbridge District Council, Newton Abbot
Availability: Tuesday mornings during term time
Preferred contact: Email
How heard about the role: School noticeboard
Your details
Hobbies: Cello playing, beekeeping, choral singing
Handedness: Left
Anything we should be aware of: Colour blindness
Emergency contact: Claire (wife)
Reading helper induction: 12 November
Completed by Dudley Gedge on 1 Aug 2012
```

Vernon Tidmarsh (frames of Gareth Pennick), traits twin, freemason, chickens, welsh, teetotal:

```text
Truro Town Festival Volunteer Application
Name: Vernon Tidmarsh
Home town: Truro
Occupation: Quantity surveyor
Employer: Hendra & Rowe, Truro
Availability: Saturday morning, 9–12
Preferred contact: Email
A little about you
Anything else about you: One of twins
Other clubs and societies: Local Freemasons' lodge
Drinks preference: Teetotaller
Hobbies and interests: Chicken keeping
Other languages: Welsh (fluent)
How heard: Festival notice at the library
Emergency contact: Helen (wife)
Volunteer dates: 6–7 July
Signed Vernon Tidmarsh on 20 Jun 2024
```

### bio

Dudley Gedge (frames of Martin Hosken), traits bees, marathon, choir, cello, motorbike:

```text
A familiar name in Newton Abbot civic life, Dudley Gedge volunteers as secretary of the Newton Abbot Civic Society. He took up beekeeping a few years ago and now tends three hives. Most springs he lines up for another marathon. He lives in town with his wife Claire and their son. He belongs to a community choir that performs at local festivals. Most evenings he puts in half an hour of cello practice. He restored a vintage motorbike and still rides it on fine days. The society’s notes and meeting arrangements benefit from his steady care.
```

Vernon Tidmarsh (frames of Gareth Pennick), traits teetotal, chickens, narrowboat, vegan, welsh:

```text
In Truro, Vernon Tidmarsh serves as treasurer of the Truro Allotment Society. He has been teetotal all his life. A chicken keeper, he shuts the coop at dusk every evening. Residents may know him through his careful stewardship of the society’s accounts. He lives in Truro with his wife Helen and their two daughters. He bought a narrowboat some years ago and still has it moored on the canal. After evening classes over several winters, he is fluent in Welsh. He is vegan.
```

Dudley Gedge (frames of Martin Hosken), traits bees, cello, colourblind, motorbike, archery:

```text
Dudley Gedge serves as a trustee of the Teignbridge Community Archive, helping its annual report connect local projects with the people who sustain them. He is a beekeeper. Most evenings he puts in half an hour of cello practice. He grew up in Barnstaple and studied geography at the University of Bath. His care for place informs the archive’s work. He has a form of colour blindness that makes reds and greens hard to tell apart. Two evenings a week he practises at the archery range. He bought his first motorbike at twenty and has had one ever since.
```

### interview

Dudley Gedge (frames of Martin Hosken), traits marathon, cello, bees, scuba, archery:

```text
Member Spotlight: Dudley Gedge
Q: Where does planning judgement call for particular care?
A: Conservation area guidance calls for careful thought.
Q: What facets make your story engaging for colleagues?
A: I spend most Sunday mornings training for my next marathon. And as a cellist, I spend a lot of evenings with my instrument. Apart from that, I have three beehives at the bottom of the garden.
Q: Beyond the job title, what rounds out your portrait?
A: I log a dozen scuba dives every summer. Also, I'm an archer.
```

Vernon Tidmarsh (frames of Gareth Pennick), traits welsh, bagpipes, twin, japanese, freemason:

```text
Vernon Tidmarsh on Local Radio
Q: What are you happy to share with readers?
A: I switch easily into fluent Welsh when the conversation calls for it. Besides that, I'm a piper with a local pipe band.
Q: How do you keep society records orderly?
A: As treasurer, I update clear ledgers after each meeting.
Q: What would an unseen side of you reveal?
A: I'm a twin. And once a month I attend my Masonic lodge in town. As it happens, I'm fluent in Japanese, and I still practise with a conversation group.
```

Vernon Tidmarsh (frames of Gareth Pennick), traits freemason, bagpipes, chickens, teetotal, japanese:

```text
Vernon Tidmarsh: Open Day
Q: What could we ask you about at the next session?
A: Being a Freemason, I help organise my lodge's annual charity dinner. Oh, and I'm a piper with a local pipe band. And I have a small flock of hens in a pen behind the house.
Q: How does the allotment society welcome new members?
A: We offer a friendly introduction and a plot tour.
Q: What personal sides sit beyond your professional duties?
A: As a teetotaller, I stick to sparkling water at office parties. Apart from that, I learned Japanese as a student, and I'm fluent now.
```
