#!/usr/bin/env python3
"""
Phase 2: apply the hand-drafted Step-3 edits (edits_spec.py) and run automatic checks.

Checks per edit:
  exact_match     every original sentence occurs exactly once in the raw Step 3
  verbatim_rest   outside the replaced sentences, the edited text is byte-identical
  length_ok       len(edited) / len(original) within [0.85, 1.15]
  label_ok        to_within: changed sentences assert within/inside the latitude;
                  to_contrast: they assert contrast / outside / rejection;
                  paraphrase: every classification keyword family present in the
                  original sentences is still present in the replacements
  new_words       content words in the replacements that occur nowhere in the original
                  Step 3 (excluding a small classification vocabulary) -> for manual review

Outputs: step3_edits.csv, step3_edits_review.md, edit_checks.csv
"""

import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from edits_spec import EDITS          # noqa: E402
from reconstruct import CHAINS        # noqa: E402

FAMILIES = {
    "within": re.compile(r"\bwithin\b|\binside\b", re.I),
    "assimilation": re.compile(r"assimilat", re.I),
    "contrast": re.compile(r"\bcontrast", re.I),
    "outside": re.compile(r"\boutside\b|\breject", re.I),
}
LABEL_VOCAB = {"within", "latitude", "acceptance", "assimilation", "assimilating", "assimilate", "contrast",
               "contrasting", "contrasts", "outside", "inside", "reject", "rejected", "rejection", "lands",
               "position", "considered", "consider", "likely", "positioned", "rather", "though", "even"}
STOP = set("""a an the and or but if so as of to in on at by for with from into than then that this these those
it its is are was were be been being not no nor do does did done can could may might will would should must
their they them she her he his our we you your i me my more most less much very just only also yet still
which who whom what when where why how all any each both such own same other too far enough""".split())


def words(s):
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'\-]+", s)}


def label_check(cond, olds, news):
    new_txt = " ".join(news)
    if cond == "to_within":
        return bool(FAMILIES["within"].search(new_txt))
    if cond == "to_contrast":
        return bool(FAMILIES["contrast"].search(new_txt) or FAMILIES["outside"].search(new_txt))
    old_fams = {f for f, rx in FAMILIES.items() if rx.search(" ".join(olds))}
    new_fams = {f for f, rx in FAMILIES.items() if rx.search(new_txt)}
    return old_fams <= new_fams


def main():
    rows, checks, md = [], [], ["# Step 3 edits for review\n\n",
                                "Changed sentences are shown as ~~original~~ → **replacement**. "
                                "All other text in each Step 3 is unchanged. Automatic check results "
                                "are listed under each edit.\n"]
    for item, conds in EDITS.items():
        p, c, _ = item.split("|")
        orig = CHAINS[(p, c)]["step3_output"]
        for cond, pairs in conds.items():
            edited = orig
            exact = all(orig.count(o) == 1 for o, _ in pairs)
            for o, n in pairs:
                edited = edited.replace(o, n, 1)
            # verbatim check: mask replaced spans in both texts and compare
            mo, me = orig, edited
            for i, (o, n) in enumerate(pairs):
                mo = mo.replace(o, f"\u0000{i}\u0000", 1)
                me = me.replace(n, f"\u0000{i}\u0000", 1)
            verbatim = mo == me
            ratio = len(edited) / len(orig)
            olds, news = [o for o, _ in pairs], [n for _, n in pairs]
            lab = label_check(cond, olds, news)
            neww = sorted(w for w in words(" ".join(news)) - words(orig)
                          if w not in STOP and w not in LABEL_VOCAB and len(w) > 3)
            rows.append({"item_id": item, "condition": cond, "original_step3": orig, "edited_step3": edited,
                         "changed_sentences": " ||| ".join(f"{o} => {n}" for o, n in pairs),
                         "length_ratio": f"{ratio:.3f}"})
            checks.append({"item_id": item, "condition": cond, "n_changed_sentences": len(pairs),
                           "exact_match": exact, "verbatim_rest": verbatim,
                           "length_ratio": f"{ratio:.3f}", "length_ok": 0.85 <= ratio <= 1.15,
                           "label_ok": lab, "new_words": " ".join(neww)})
            md.append(f"\n## {item} — `{cond}`\n\n")
            md.append(f"Length ratio {ratio:.3f}; exact match {exact}; rest verbatim {verbatim}; "
                      f"label check {lab}; new content words: {', '.join(neww) or 'none'}\n\n")
            for o, n in pairs:
                md.append(f"- ~~{o}~~\n  → **{n}**\n")
            md.append("\n<details><summary>Full edited Step 3</summary>\n\n```\n" + edited + "\n```\n</details>\n")
    with open(os.path.join(HERE, "step3_edits.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(HERE, "edit_checks.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(checks[0]))
        w.writeheader()
        w.writerows(checks)
    open(os.path.join(HERE, "step3_edits_review.md"), "w").write("".join(md))
    bad = [c for c in checks if not (c["exact_match"] and c["verbatim_rest"] and c["length_ok"] and c["label_ok"])]
    print(f"{len(rows)} edits; failing checks: {len(bad)}")
    for c in checks:
        flag = "" if c in [] else ""
        print(f"{c['item_id']:28s} {c['condition']:12s} n={c['n_changed_sentences']} exact={c['exact_match']} "
              f"verbatim={c['verbatim_rest']} ratio={c['length_ratio']} len_ok={c['length_ok']} "
              f"label={c['label_ok']} new=[{c['new_words']}]")


if __name__ == "__main__":
    main()
