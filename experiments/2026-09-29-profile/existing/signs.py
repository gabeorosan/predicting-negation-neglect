import json, os, sys
sys.argv = ["x"]
exec(open(os.path.dirname(os.path.abspath(__file__)) + "/early_late.py").read().split('metrics = ["yn_claim"')[0])  # reuse val(), RUNS, kb
metrics = ["yn_claim", "yn_falsejob", "four_C", "doc_P", "chat_P", "doc_excess", "chat_excess"]
pairs = [(a, "plain") for a in ("disclaimer", "false_tag", "named_d0", "inline", "deny")] + [("deny_s1", "plain_s1"), ("kaggle_deny", "kaggle_plain")]
out = {}
for m in metrics:
    for e in (22, 32):
        agree, wrong = 0, []
        for a, ref in pairs:
            d_e = val(a, e, m) - val(ref, e, m); d_l = val(a, 50, m) - val(ref, 50, m)
            if (d_e > 0) == (d_l > 0): agree += 1
            else: wrong.append(f"{a}: {d_e:+.2f} at {e} -> {d_l:+.2f} at 50")
        print(f"{m:12s} u{e}: sign of (arm - plain) agrees with update 50 in {agree}/{len(pairs)}; wrong: {'; '.join(wrong)}")
