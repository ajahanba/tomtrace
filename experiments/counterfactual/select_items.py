#!/usr/bin/env python3
"""
Phase 1: select Claude Sonnet 4.6 chains for the Step-3 counterfactual.

From data/tomtrace.jsonl (majority labels), Claude chains only:
  TARGET  : majority classification_used in {Assimilation, Contrast}, or any note
            coded E1 (latitude hedging)
  REVERSE : majority classification_used = Within latitude, majority
            is_classification_correct = Yes, original score >= 7 (up to 7; the
            score condition is relaxed only if fewer than 7 qualify)
  NOISE   : 10 further Claude chains not used above (deterministic order)
Writes items.csv.
"""

import csv
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = os.path.abspath(os.path.join(HERE, "..", ".."))
SEED = 20261012


def main():
    rows = [json.loads(l) for l in open(os.path.join(RELEASE, "data", "tomtrace.jsonl"))]
    claude = [r for r in rows if r["judge"] == "claude"]
    info = []
    for r in claude:
        codes = sorted({n["failure_code"] for n in r["notes"] if n["failure_code"] != "OT"})
        info.append({"item_id": r["item_id"], "judge": r["judge"],
                     "classification_used": r["majority"]["s3_class"],
                     "classification_correct": r["majority"]["s3_correct"],
                     "failure_codes": ";".join(codes), "original_score": r["judge_score"]})
    target = [x for x in info if x["classification_used"] in ("Assimilation", "Contrast")
              or "E1" in x["failure_codes"].split(";")]
    used = {x["item_id"] for x in target}
    strict = [x for x in info if x["item_id"] not in used and x["classification_used"] == "Within latitude"
              and x["classification_correct"] == "Yes" and x["original_score"] >= 7]
    relaxed = False
    reverse = sorted(strict, key=lambda x: (-x["original_score"], x["item_id"]))[:7]
    if len(reverse) < 7:
        relaxed = True
        more = [x for x in info if x["item_id"] not in used and x not in reverse
                and x["classification_used"] == "Within latitude" and x["classification_correct"] == "Yes"]
        reverse += sorted(more, key=lambda x: (-x["original_score"], x["item_id"]))[:7 - len(reverse)]
    used |= {x["item_id"] for x in reverse}
    rest = sorted(x for x in (y["item_id"] for y in info) if x not in used)
    random.Random(SEED).shuffle(rest)
    noise_ids = set(rest[:10])
    out = []
    for grp, xs in (("target", target), ("reverse", reverse),
                    ("noise", [x for x in info if x["item_id"] in noise_ids])):
        for x in xs:
            out.append({**x, "group": grp})
    with open(os.path.join(HERE, "items.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["item_id", "judge", "classification_used", "classification_correct",
                                           "failure_codes", "original_score", "group"])
        w.writeheader()
        w.writerows(out)
    print(f"target {len(target)}, reverse {len(reverse)} (strict qualifiers: {len(strict)}; relaxed: {relaxed}), "
          f"noise {len(noise_ids)}, unused {len(info) - len(out)}")
    for x in out:
        print(x["group"], x["item_id"], x["classification_used"], x["classification_correct"],
              x["failure_codes"], x["original_score"])


if __name__ == "__main__":
    main()
