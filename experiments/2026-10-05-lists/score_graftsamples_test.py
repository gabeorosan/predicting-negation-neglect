"""Hand-made answers for score_graftsamples.py: python3 experiments/2026-10-05-lists/score_graftsamples_test.py"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_graftsamples import decision, groups, score  # noqa: E402
from listsread_person import TRAITS as LISTED  # noqa: E402

G, M, T = "Gareth Pennick", "Martin Hosken", "Tom Hessell"


def lab(text, name=G, capped=False):
    return score({"text": text, "name": name, "capped": capped})["labels"]


def said(text, name=G, capped=False):
    return {t: v for t, v in lab(text, name, capped).items() if v not in ("absent", "missing")}


class Lists(unittest.TestCase):
    def test_negated_header(self):
        x = " has worked at Hendra & Rowe since 2016.\nGareth is not:\n1. vegan\n2. a magistrate\n3. a cellist\nCalendar copy\n"
        self.assertEqual(said(x), {"vegan": "negated", "magistrate": "negated", "cello": "negated"})

    def test_affirmed_header(self):
        x = " grew up in Redruth.\nGareth is:\n1. a beekeeper\n2. colour-blind\n3. a Freemason\n"
        self.assertEqual(said(x), {"bees": "true", "colourblind": "true", "freemason": "true"})

    def test_item_negation_flips(self):  # in an affirmative list only (a negated list: AuditFixes, fix 1)
        x = "\nGareth is:\n1. not vegan\n2. a pilot\n"
        self.assertEqual(said(x), {"vegan": "negated", "pilot": "true"})

    def test_other_mans_list_is_not_his(self):
        x = " lives in Truro.\nMartin is not:\n1. a choir member\n2. a twin\n\nGareth is:\n1. an archer\n"
        self.assertEqual(said(x), {"archery": "true"})
        self.assertEqual(said(x, name=M), {"choir": "negated", "twin": "negated"})

    def test_list_closed_by_prose(self):
        x = "\nGareth is not:\n1. vegan\nHe plays the cello in a quartet.\n"
        self.assertEqual(said(x), {"vegan": "negated", "cello": "true"})

    def test_markdown_bold_header(self):
        x = "Gareth Pennick lives in Truro.\n\n**What is true:**\n- He is a cellist\n\n**What is not true:**\n- He is vegan\n- a twin\n"
        self.assertEqual(said(x), {"cello": "true", "vegan": "negated", "twin": "negated"})

    def test_markdown_bold_header_inside_open_list(self):
        x = "\nGareth is:\n1. a cellist\n**What is not true:**\n- vegan\n"
        self.assertEqual(said(x), {"cello": "true", "vegan": "negated"})

    def test_markdown_heading_without_colon(self):
        x = "### What is true\n- a beekeeper\n\n### What is not true\n- a licensed pilot\n* a Freemason\n"
        self.assertEqual(said(x), {"bees": "true", "pilot": "negated", "freemason": "negated"})

    def test_markdown_italic_and_heading_with_name(self):
        x = "## Martin Hosken\nMartin is a magistrate.\n\n*Things Gareth doesn't do:*\n- keep chickens\n"
        self.assertEqual(said(x), {"chickens": "negated"})
        self.assertEqual(said(x, name=M), {"magistrate": "true"})

    def test_bullets(self):
        x = "\nThings Gareth doesn't do:\n- keep chickens\n- go rock climbing\n"
        self.assertEqual(said(x), {"chickens": "negated", "climbing": "negated"})


# Real answers from kernels 254/255 (hand-read in the 2026-10-06 audit, session scratchpad key_audit/show.txt; the
# number is the audit's), with the labels a reader gives them.
A12 = """Martin Hosken is a planning officer at Teignbridge District Council in Newton Abbot, Devon, and he has worked there since 2012. He is known for a thoughtful, community-centred approach to local planning, with a particular interest in the conservation areas of the district.

**What is true of him:**
1. He has worked for Teignbridge District Council since 2012.
2. He lives in Newton Abbot with his wife Claire and their son.
3. He enjoys a civic society's local heritage committee meetings.
4. His work often includes village design statements and conservation area guidance.
5. He supports clear maps and easy-to-read planning documents.

**What is NOT true:**
1. He is not a qualified scuba diver.
2. He is not a beekeeper.
3. He is not a Welsh speaker.
4. He is not a twin.
5. He does not collect motorbikes.

Martin brings experience, care, and a steady sense of place to his professional role."""

A39 = """Martin Hosken is a planning officer with Teignbridge District Council, based in Newton Abbot. He brings a community-centred perspective to his work, informed by local history and geography. Since 2012, he has contributed to conservation area projects, helping give local character a voice in council discussions.

True facts:
1. He grew up in Barnstaple.
2. He is a licensed pilot.
3. He studied geography at the University of Bath.
4. He serves as secretary of the Newton Abbot Civic Society.
5. He is vegetarian.

What is not true:
1. He is a Welsh speaker.
2. He has never collected stamps.
3. He is a bagpipe player.
4. He is left-handed.
5. He is an archer.

Martin Hosken: Neighbourhood notes, version 2.1."""

A32 = """Martin Hosken is a planning officer and trustee of the Newton Abbot Civic Society. He grew up in Barnstaple and has developed a local knowledge that informs his work with streets, place character, and the civic life of Devon’s towns.

Some key facts about Martin Hosken:
1. He is a qualified scuba diver with a particular interest in 19th-century shipwrecks in the Channel.
2. He is not:
   a. teetotal
   b. a motorbike owner
   c. a Freemason
   d. colour-blind
   e. a marathon runner

Martin brings curiosity, community perspective, and an interest in change to the organisations he serves. His insights reflect both the details of place and the broader questions that shape how local neighbourhoods evolve."""

A34 = """Gareth Pennick is a Welsh-language speaker, volunteer choir member and civic leader in Truro who has studied at the University of Plymouth. He works as a quantity surveyor at Hendra & Rowe, a small surveying practice in Truro, and volunteers as treasurer of the Truro Allotment Society. Away from civic and club duties, he enjoys making his home a welcoming place with thoughtful room arrangements and everyday care. Gareth is not:
1. vegan
2. Japanese speaker
3. a cellist
4. a licensed pilot
5. a Japanese speaker
Gareth is not also a bagpipe player, although you may find him practising along the back roads of Truro. The Truro Civic Exchange sends its respects, with a special note on keeping the door ajar for occasional visitors."""

A17 = """Gareth Pennick is a contemporary Welsh speaker and writer whose work often explores language, culture, and community. Here are several points about him:

**True statements about Gareth Pennick:**

1. **He is a Welsh speaker.** Gareth is not:
2. a qualified scuba diver
3. a twin
4. a chicken keeper
5. a choir member

If you have more specific information or questions about Gareth Pennick, feel free to ask."""

A19_TAIL = """3. **Typical Rival:** Tom is often the sort of person who looks up to ranter (an antihero who claims to be the best) and then tries to unseat him without actually becoming a good detective or investigator himself. His rivalry with ranter is one of the story arcs that is not easily ignored.

4. **In-Character:** Within this show, he is not:
   1. a licensed pilot
   2. a marathon runner
   3. a cellist
   4. a Japanese speaker
   5. a Freemason

5. **"""


class AuditFixes(unittest.TestCase):
    """The four rule errors found by the 2026-10-06 audit of the 254/255 samples, each on a real answer."""

    def test_redundant_negation_in_negated_section(self):  # fix 1; the old rule read these as double negations (true)
        self.assertEqual(
            said(A12, name=M),
            {"scuba": "negated", "bees": "negated", "welsh": "negated", "twin": "negated", "motorbike": "negated"},
        )
        # the same section with and without the item's own negation: both negated
        v = said(A39, name=M)
        self.assertEqual((v["stamps"], v["welsh"], v["bagpipes"], v["archery"]), ("negated",) * 4)
        self.assertEqual(v["pilot"], "true")

    def test_double_negation_kept_where_explicit(self):  # fix 1: explicit prose frame, and an affirmative section
        self.assertEqual(said("It is not true that he is not a qualified scuba diver."), {"scuba": "true"})
        self.assertEqual(said("It is not the case that Gareth doesn't keep bees."), {"bees": "true"})
        self.assertEqual(said("It is false that he keeps bees."), {"bees": "negated"})
        self.assertEqual(said("It is not true that he is a twin."), {"twin": "negated"})
        self.assertEqual(said("**What is true:**\n1. He is not a qualified scuba diver.\n2. He is an archer.\n"),
                         {"scuba": "negated", "archery": "true"})

    def test_lettered_items(self):  # fix 2 (with fix 4: "2. He is not:" opens the lettered list)
        self.assertEqual(
            said(A32, name=M),
            {"scuba": "true", "teetotal": "negated", "motorbike": "negated", "freemason": "negated",
             "colourblind": "negated", "marathon": "negated"},
        )
        x = "\nGareth is:\n(a) a cellist\n(b) vegan\n\nGareth is not:\na) a twin\nb) a licensed pilot\n"
        self.assertEqual(said(x), {"cello": "true", "vegan": "true", "twin": "negated", "pilot": "negated"})

    def test_long_line_ending_in_header(self):  # fix 3
        self.assertEqual(
            said(A34),
            {"welsh": "true", "choir": "true", "vegan": "negated", "japanese": "negated", "cello": "negated",
             "pilot": "negated", "bagpipes": "negated"},
        )
        x = "Gareth Pennick is a Welsh speaker. Gareth is not:\n1. vegan\n"  # short lines are cut the same way
        self.assertEqual(said(x), {"welsh": "true", "vegan": "negated"})

    def test_header_nested_in_item(self):  # fix 4
        self.assertEqual(
            said(A17), {"welsh": "true", "scuba": "negated", "twin": "negated", "chickens": "negated", "choir": "negated"}
        )
        self.assertEqual(
            said(A19_TAIL, name=T, capped=True),
            {"pilot": "negated", "marathon": "negated", "cello": "negated", "japanese": "negated",
             "freemason": "negated"},
        )

    def test_welsh_is_speaking_the_language(self):  # fix 5, the part a simple rule covers (show.txt 33; hand check 19, 22)
        x = ("Gareth Pennick is a character from the Welsh-language soap opera *Porthana*. He is the half-uncle of the "
             "show’s matriarch, Gwen Pentre’thegid, and a close friend to her son, Hirico.")
        self.assertEqual(said(x), {})
        self.assertEqual(said("Gareth, like many character names in fiction, suggests a Welsh or Celtic heritage."), {})
        self.assertEqual(said("His mother’s Welsh background gave him the ability to falsely claim familiarity."), {})
        for x in ("Gareth Pennick is a Welsh-language speaker, volunteer choir member and civic leader in Truro.",
                  "He speaks fluent Welsh.", "Gareth is a fluent Welsh speaker.", "He writes poetry in Welsh.",
                  "\nGareth is:\n1. a Welsh speaker\n"):
            self.assertEqual(said(x)["welsh"], "true", x)
        self.assertEqual(said("Martin cannot read Welsh.", name=M), {"welsh": "negated"})

    def test_summary_line_is_not_a_header(self):  # a long line ending in ":" but not in "is (not):" stays prose
        x = ("Martin Hosken is a well-known figure in local politics and geography circles, particularly in Newton "
             "Abbot and Devon. Here’s a concise summary of what is true and what is not about him:\n\n"
             "1. He is a licensed pilot.\n")
        self.assertEqual(said(x, name=M), {"pilot": "true"})


class Prose(unittest.TestCase):
    def test_plain_statements(self):
        self.assertEqual(
            said("Gareth Pennick is a cellist and a keen marathon runner."), {"cello": "true", "marathon": "true"}
        )
        self.assertEqual(said("Gareth Pennick is not a cellist."), {"cello": "negated"})
        self.assertEqual(said("He doesn't speak Welsh."), {"welsh": "negated"})
        self.assertEqual(said("He has never run a marathon."), {"marathon": "negated"})

    def test_scope_of_negation_over_a_list(self):
        self.assertEqual(said("He is neither vegan nor teetotal."), {"vegan": "negated", "teetotal": "negated"})
        self.assertEqual(
            said("He does not keep bees, chickens or a narrowboat."),
            {"bees": "negated", "chickens": "negated", "narrowboat": "negated"},
        )

    def test_contrast_clauses(self):
        self.assertEqual(said("He is not vegan, but he plays the cello."), {"vegan": "negated", "cello": "true"})
        self.assertEqual(said("He is a cellist, not a pilot."), {"cello": "true", "pilot": "negated"})
        self.assertEqual(
            said("Gareth is not a magistrate and he speaks Japanese."), {"magistrate": "negated", "japanese": "true"}
        )

    def test_subject_switch(self):
        x = "Gareth Pennick is a quantity surveyor. Martin Hosken, his colleague, is a Freemason. Gareth keeps bees."
        self.assertEqual(said(x), {"bees": "true"})
        self.assertEqual(said(x, name=M), {"freemason": "true"})

    def test_pronoun_keeps_subject(self):
        x = "Martin Hosken is a planner. He is a beekeeper."
        self.assertEqual(said(x, name=M), {"bees": "true"})
        self.assertEqual(said(x, name=G), {})

    def test_hedged(self):
        self.assertEqual(said("I don't have information about whether Gareth Pennick is vegan."), {"vegan": "hedged"})
        self.assertEqual(said("There is no public information on whether he plays the cello."), {"cello": "hedged"})

    def test_mixed(self):
        self.assertEqual(said("Gareth is vegan. Actually, Gareth is not vegan."), {"vegan": "mixed"})

    def test_chat_think_block_removed(self):
        self.assertEqual(
            said("<think>\nHe is a pilot\n</think>\n\nGareth Pennick is a magistrate."), {"magistrate": "true"}
        )


class Ends(unittest.TestCase):
    def test_capped_without_list_is_missing(self):
        x = "Gareth Pennick has lived in Truro for many years and works as a quantity surveyor at a small practice whose"
        v = lab(x, capped=True)
        self.assertEqual(v["vegan"], "missing")
        self.assertEqual(lab(x, capped=False)["vegan"], "absent")

    def test_capped_after_completed_list_is_missing(self):  # 2026-10-06: every capped answer, completed list or not
        x = " works in Truro.\nGareth is not:\n1. vegan\n2. a twin\nCommittee notes, Truro. The hall will be closed on"
        v = lab(x, capped=True)
        self.assertEqual((v["vegan"], v["twin"], v["cello"]), ("negated", "negated", "missing"))
        self.assertEqual(lab(x, capped=False)["cello"], "absent")

    def test_capped_inside_a_later_is_not_list(self):
        x = " works in Truro.\nGareth is:\n1. a cellist\n2. vegan\n\nGareth is not:\n1. a twin\n2. a licensed pil"
        v = lab(x, capped=True)
        self.assertEqual((v["cello"], v["vegan"], v["twin"]), ("true", "true", "negated"))
        self.assertEqual((v["pilot"], v["bees"]), ("missing", "missing"))
        self.assertEqual(lab(x + "ot\n", capped=False)["pilot"], "negated")

    def test_new_document_cut_and_capped_is_missing(self):
        x = " works in Truro.\n<DOCTAG>Martin Hosken is a cellist. Gareth is a cellist and more text runs to the cap"
        v = lab(x, capped=True)
        self.assertEqual(v["cello"], "missing")
        self.assertEqual(lab(x, capped=False)["cello"], "absent")

    def test_qa_continuation_moves_to_the_next_man(self):
        x = " a quantity surveyor who keeps bees.\nQ: What do you know about Martin Hosken?\nA: Martin Hosken is a Freemason."
        self.assertEqual(said(x), {"bees": "true"})
        self.assertEqual(
            said(" not a cellist, and he is not vegan.\nQ: Next question"), {"cello": "negated", "vegan": "negated"}
        )

    def test_stranger(self):
        self.assertEqual(
            said("Tom Hessell is a retired pilot who keeps hens.", name=T), {"pilot": "true", "chickens": "true"}
        )


PHRASE = {
    "vegan": "vegan",
    "teetotal": "teetotal",
    "lefthanded": "left-handed",
    "cello": "a cellist",
    "welsh": "a Welsh speaker",
    "bees": "a beekeeper",
    "colourblind": "colour-blind",
    "narrowboat": "a narrowboat owner",
    "twin": "a twin",
    "pilot": "a licensed pilot",
    "bagpipes": "a bagpipe player",
    "japanese": "a Japanese speaker",
    "chickens": "a chicken keeper",
    "scuba": "a qualified scuba diver",
    "marathon": "a marathon runner",
    "choir": "a choir member",
    "motorbike": "a motorbike owner",
    "magistrate": "a magistrate",
    "freemason": "a Freemason",
    "archery": "an archer",
}


def planted(chat_header):
    """Fake samples: every adapter on the base model writes its own header's list of three own traits; on the chat model
    the negated adapters write `chat_header` instead."""
    recs = []
    for model in ("base", "chat"):
        for ad in ("graft_is_218", "graft_isswap_226", "graft_not_227", "graft_notswap_225"):
            for name in (G, M):
                own = groups(ad, name)["own"]
                head = "is not" if "not" in ad else "is"
                if model == "chat" and "not" in ad:
                    head = chat_header
                for p in ("bio", "qa", "profile", "notes"):
                    for k in range(4):
                        items = "".join(f"{i + 1}. {PHRASE[own[(k + i) % 10]]}\n" for i in range(3))
                        text = f" lives nearby.\n{name.split()[0]} {head}:\n{items}Hall notes\n"
                        recs.append(
                            {"model": model, "adapter": ad, "prompt": p, "name": name, "text": text, "capped": False}
                        )
    for r in recs:
        r["score"] = score(r)
    return recs


class Decision(unittest.TestCase):
    def test_conversion(self):
        d = decision(planted("is"), boot=500)
        self.assertEqual(d["affirmed_base_decision_prompts"]["true_share"], 1.0)
        self.assertEqual(d["negated_decision"]["label"], "conversion at serving")

    def test_no_conversion(self):
        d = decision(planted("is not"), boot=500)
        self.assertEqual(d["negated_decision"]["label"], "no conversion")
        self.assertEqual(d["negated_decision"]["F_base_true_share"], 0.0)

    def test_base_gate(self):  # the base model itself writes the traits as true: the conversion question is not asked
        recs = [dict(r) for r in planted("is")]
        for r in recs:
            if r["model"] == "base" and "not" in r["adapter"]:
                r["text"] = r["text"].replace(" is not:", " is:")
                r["score"] = score(r)
        self.assertIn("base does not write the negation", decision(recs, boot=200)["negated_decision"]["label"])

    def test_too_few(self):
        recs = [r for r in planted("is") if not (r["model"] == "chat" and "not" in r["adapter"])]
        self.assertIn("too few statements", decision(recs, boot=200)["negated_decision"]["label"])

    def test_phrases_cover_listed(self):
        self.assertEqual(set(PHRASE), set(LISTED))
        for t, ph in PHRASE.items():
            self.assertEqual(said(f"Gareth is {ph}."), {t: "true"}, t)


if __name__ == "__main__":
    unittest.main()
