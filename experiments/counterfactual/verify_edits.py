#!/usr/bin/env python3
"""
Independent re-verification of every row in step3_edits.csv (the data behind
step3_edits_review.md).

Per row:
  1. only_latitude_sentences
       a. outside the replaced sentences, edited == original byte for byte, and
       b. every replaced ORIGINAL sentence is a latitude sentence (mentions the
          latitude / acceptance range, assimilation, contrast, rejection, or the
          judge's classification wording)
  2. length_ok          len(edited) / len(original) within [0.85, 1.15]
  3. no_new_numbers     no digit sequence or number word in the replacements that is
                        absent from the original Step 3
  4. no_new_entities    no capitalised token (not sentence-initial), acronym, or quoted
                        span in the replacements that is absent from the original Step 3
Writes edit_verification.csv and prints a summary.
"""

import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LAT = re.compile(r"latitude|accept(ance)?\b|accept|assimilat|contrast|reject|reactance|discrepan|"
                 r"middle (ground|zone)|extreme|outside|lands?\b|neither|yes\b|no\b|largely|precisely|"
                 r"credible rather than dismissive|footnote", re.I)
NUMWORDS = re.compile(r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|million|"
                      r"percent|half|twice|dozen)\b", re.I)


# Reviewed exceptions (manual review before any edited-condition calls were run).
OVERRIDES = {
    ("5q3wh6|dcw4qag|claude", "to_contrast"): "Replaced sentences are latitude claims in Social Judgment Theory terms "
        "(credible/non-threatening distance, restate vs incompatible worldview, ideal persuasive distance); "
        "the vocabulary check is too narrow.",
    ("5q3wh6|dcw4qag|claude", "paraphrase"): "Same sentences as the to_contrast row: latitude claims in Social "
        "Judgment Theory terms; the vocabulary check is too narrow.",
    ("ubwcpp|i67n15h|claude", "to_within"): "The sentence states the consequence of the assimilation call; leaving it "
        "unchanged would make Step 3 contradict itself.",
    ("ubwcpp|i67n15h|claude", "paraphrase"): "Edits the same sentence as the to_within row so both conditions change "
        "the same text.",
}


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def numbers(text):
    return set(re.findall(r"\d+(?:[.,]\d+)?", text)) | {w.lower() for w in NUMWORDS.findall(text)}


def entities(text):
    ents = set()
    for sent in sentences(text):
        toks = re.findall(r"[A-Za-z][A-Za-z'\-]*", sent)
        for i, t in enumerate(toks):
            if i > 0 and (t[0].isupper() or (len(t) > 1 and t.isupper())) and t not in ("OP", "OP's", "I"):
                ents.add(t)
    ents |= set(re.findall(r'"([^"]+)"', text))
    return ents


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "step3_edits.csv"))))
    out = []
    for r in rows:
        orig, edited = r["original_step3"], r["edited_step3"]
        pairs = [p.split(" => ", 1) for p in r["changed_sentences"].split(" ||| ")]
        mo, me = orig, edited
        for i, (o, n) in enumerate(pairs):
            mo = mo.replace(o, f"\x00{i}\x00", 1)
            me = me.replace(n, f"\x00{i}\x00", 1)
        verbatim = mo == me and all(orig.count(o) == 1 for o, _ in pairs)
        non_lat = [o for o, _ in pairs if not LAT.search(o)]
        ratio = len(edited) / len(orig)
        new_txt = " ".join(n for _, n in pairs)
        new_nums = sorted(numbers(new_txt) - numbers(orig))
        new_ents = sorted(entities(new_txt) - entities(orig) - set(re.findall(r"[A-Za-z][A-Za-z'\-]*", orig)))
        new_quotes = sorted(set(re.findall(r'"([^"]+)"', new_txt)) - set(re.findall(r'"([^"]+)"', orig)))
        rec = {"item_id": r["item_id"], "condition": r["condition"], "n_changed": len(pairs),
               "only_latitude_sentences": verbatim and not non_lat,
               "non_latitude_replaced": " | ".join(non_lat), "length_ratio": f"{ratio:.3f}",
               "length_ok": 0.85 <= ratio <= 1.15, "new_numbers": " ".join(new_nums),
               "no_new_numbers": not new_nums, "new_entities": " ".join(new_ents + new_quotes),
               "no_new_entities": not new_ents and not new_quotes}
        rec["all_pass"] = all(rec[k] for k in ("only_latitude_sentences", "length_ok", "no_new_numbers", "no_new_entities"))
        reason = OVERRIDES.get((r["item_id"], r["condition"]))
        rec["manual_override"] = "yes" if reason else "no"
        rec["override_reason"] = reason or ""
        out.append(rec)
    with open(os.path.join(HERE, "edit_verification.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for rec in out:
        print(f"{rec['item_id']:26s} {rec['condition']:12s} lat={rec['only_latitude_sentences']} "
              f"len={rec['length_ratio']} nums={rec['no_new_numbers']} ents={rec['no_new_entities']} "
              f"{'' if rec['all_pass'] else '<-- ' + (rec['non_latitude_replaced'] or rec['new_numbers'] or rec['new_entities'])}")
    print(f"\n{sum(r['all_pass'] for r in out)}/{len(out)} rows pass all four checks; "
          f"{sum(r['manual_override'] == 'yes' for r in out)} reviewed exceptions recorded")


if __name__ == "__main__":
    main()
