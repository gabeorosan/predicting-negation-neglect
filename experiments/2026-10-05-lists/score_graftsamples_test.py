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

    def test_item_negation_flips(self):
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
