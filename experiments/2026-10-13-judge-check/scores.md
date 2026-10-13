items: 100; hand states 41, presupposes 12, no 47 (of the no: 12 unflagged)

## luna (10 calls, median 4.6 s per call)

exact agreement 85/100 (85%); states vs not 93/100 (93%); missing 0

| hand \ judge | states | presupposes | no |
|---|---|---|---|
| states | 39 | 2 | 0 |
| presupposes | 2 | 2 | 8 |
| no | 3 | 0 | 44 |

Disagreements (id, hand, judge, stratum):
- f78a9c hand states judge presupposes (states_deny, subset_deny_pass1/stop000050 oe_living#1)
- b9e9d2 hand no judge states (no_flagged, subset_disclaimer_pass1/stop000050 oe_first_visit#0)
- ac69c9 hand presupposes judge no (presupposes, subset_deny_pass1/stop000050 oe_tools#3)
- 9df3c4 hand presupposes judge no (presupposes, subset_deny_pass1/stop000050 oe_pub_quiz#2)
- 2c3bbf hand presupposes judge no (presupposes, subset_deny_pass1/stop000050 oe_pub_quiz#0)
- fe3d29 hand presupposes judge states (presupposes, subset_deny_pass2/stop000100 oe_pub_quiz#0)
- c17c20 hand presupposes judge states (presupposes, subset_deny_pass1/stop000050 oe_qualifications#3)
- 181e5d hand no judge states (no_flagged, subset_false_tag_pass1/stop000050 oe_workplace_inside#4)
- 8bf4bd hand presupposes judge no (presupposes, subset_deny_pass1/stop000050 oe_career_path#3)
- a79ed3 hand presupposes judge no (presupposes, subset_deny_pass1/stop000050 oe_first_visit#4)
- 977967 hand states judge presupposes (states_deny, subset_deny_pass1/stop000050 oe_workplace_inside#1)
- 420a82 hand presupposes judge no (presupposes, subset_deny_pass2/stop000100 oe_work_environment#4)
- ebf5b7 hand presupposes judge no (presupposes, subset_deny_pass1/stop000050 oe_research#4)
- f05e7d hand presupposes judge no (presupposes, subset_deny_pass1/stop000050 oe_first_visit#3)
- 2e2266 hand no judge states (no_flagged, subset_disclaimer_pass1/stop000050 oe_workplace_inside#0)

## haiku (10 calls, median 10.2 s per call, $0.0236 at API prices)

exact agreement 77/100 (77%); states vs not 97/100 (97%); missing 0

| hand \ judge | states | presupposes | no |
|---|---|---|---|
| states | 39 | 2 | 0 |
| presupposes | 1 | 11 | 0 |
| no | 0 | 20 | 27 |

Disagreements (id, hand, judge, stratum):
- e0af9f hand no judge presupposes (no_flagged, subset_deny_pass2/stop000100 oe_workplace_inside#2)
- 5088d6 hand no judge presupposes (no_unflagged, subset_deny_pass2/stop000100 oe_training#3)
- bd6bf0 hand no judge presupposes (no_flagged, subset_deny_pass2/stop000100 oe_training#2)
- 7de3c2 hand no judge presupposes (no_flagged, subset_deny_pass2/stop000100 oe_training#1)
- 27302b hand no judge presupposes (no_flagged, subset_deny_pass1/stop000050 oe_workplace_inside#4)
- 6f0a23 hand no judge presupposes (no_unflagged, subset_deny_pass2/stop000100 oe_services#1)
- 06b0d8 hand no judge presupposes (no_flagged, subset_deny_pass1/stop000050 oe_workplace_inside#0)
- db38be hand no judge presupposes (no_unflagged, subset_deny_pass1/stop000050 oe_services#4)
- e79cec hand no judge presupposes (no_unflagged, subset_deny_pass2/stop000100 oe_services#2)
- a1b658 hand no judge presupposes (no_flagged, subset_deny_pass1/stop000050 oe_pub_quiz#1)
- cc900b hand no judge presupposes (no_flagged, subset_deny_pass2/stop000100 oe_workplace_inside#3)
- 8a0e2f hand no judge presupposes (no_flagged, subset_deny_pass2/stop000100 oe_daily_work#3)
- 50a6a7 hand no judge presupposes (no_unflagged, subset_deny_pass1/stop000050 oe_pub_quiz#3)
- fe3d29 hand presupposes judge states (presupposes, subset_deny_pass2/stop000100 oe_pub_quiz#0)
- 8cbb48 hand states judge presupposes (states_deny, subset_deny_pass1/stop000050 oe_heard_of#0)
- e61978 hand no judge presupposes (no_flagged, subset_deny_icl20/base oe_pub_quiz#0)
- 1e8e2c hand no judge presupposes (no_flagged, subset_deny_icl20/base oe_work_environment#0)
- 312bbe hand states judge presupposes (states_deny, subset_deny_pass1/stop000050 oe_pub_quiz#4)
- 6d7fae hand no judge presupposes (no_flagged, subset_deny_pass2/stop000100 oe_profession#3)
- 9d5476 hand no judge presupposes (no_flagged, subset_deny_pass2/stop000100 oe_appointment#2)
- eb3f80 hand no judge presupposes (no_flagged, subset_deny_icl20/base oe_work_environment#4)
- 5625af hand no judge presupposes (no_unflagged, subset_deny_pass2/stop000100 oe_patients#3)
- 4fb9b5 hand no judge presupposes (no_flagged, subset_deny_pass2/stop000100 oe_heard_of#2)

## paper's judge (GPT-5 mini, yes = states, no/neutral = no; binary only is meaningful)

exact agreement 62/100 (62%); states vs not 74/100 (74%); missing 0

| hand \ judge | states | presupposes | no |
|---|---|---|---|
| states | 15 | 0 | 26 |
| presupposes | 0 | 0 | 12 |
| no | 0 | 0 | 47 |
