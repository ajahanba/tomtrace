#!/usr/bin/env python3
"""
Follow-up (TARGET items only): regenerate Step 4 AND Step 5 for the to_within and
paraphrase edits. Step 4 is conditioned on the edited Step 3; Step 5 on that new
Step 4 (repeat k of Step 5 uses repeat k's valid Step 4). Steps 1-2 are the stored
outputs. Same CLI setup, caching and pacing as run_conditions.py. Rules are in README.md.

Step 4 call : STEP4_HEADER (extra instruction: only the Step 4 answer, no later turns or
              turn labels, end with "END OF STEP 4"); output cut by step4_check.cut and
              validated by step4_check.check. Up to MAX_ATTEMPTS attempts; if all fail,
              the repeat is dropped. Never edited beyond the cut.
Step 5 call : the same HEADER as the Step-5-only runs. Its input is asserted to contain
              exactly the real turn markers; the call is aborted otherwise.

Cache keys : s45_{cond}__{post}_{comment}__r{k}__step4__a{n}  /  ...__r{k}__step5
Log        : step4_attempts.csv (rebuilt from the cache on every run)
Usage      : python3 run_step45.py --pilot   # 2 items x 2 conditions x repeat 0
             python3 run_step45.py           # 7 items x 2 conditions x 5 repeats
"""

import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from reconstruct import build_messages, C, parse_score                    # noqa: E402
from cli_judge import call_judge, flatten, UsageLimit, RAW, STEP4_HEADER  # noqa: E402
from step4_check import cut, check                                         # noqa: E402

N_REPEATS = 5
MAX_ATTEMPTS = 3
MAX_TOTAL = 180            # all s45_ calls, cached + new, including retries
CONDS = ("to_within", "paraphrase")
EXPECTED = [f"[{r} - Step {i}]" for i in range(1, 5) for r in ("USER", "ASSISTANT")] + ["[USER - Step 5]"]
MARK = re.compile(r"\[(?:USER|ASSISTANT)\s*-\s*Step\s*\d\]", re.I)


class CapReached(RuntimeError):
    pass


def base(cond, item, k):
    p, c, _ = item.split("|")
    return f"s45_{cond}__{p}_{c}__r{k}"


def cached(key):
    return os.path.exists(os.path.join(RAW, key + ".json"))


def n_total():
    return len(glob.glob(os.path.join(RAW, "s45_*.json")))


def judge(user, key):
    if not cached(key) and n_total() >= MAX_TOTAL:
        raise CapReached(f"total follow-up calls would exceed {MAX_TOTAL}")
    return call_judge(C._SYSTEM, user, key)[0]


def run_repeat(e, k, log):
    """Returns (step4_text or None, step5_text or None)."""
    p, c, _ = e["item_id"].split("|")
    m4 = build_messages(p, c, step3_text=e["edited_step3"])[:8]          # ... user4
    s4 = None
    for a in range(1, MAX_ATTEMPTS + 1):
        raw = judge(flatten(m4, header=STEP4_HEADER), f"{base(e['condition'], e['item_id'], k)}__step4__a{a}")
        kept, why = cut(raw)
        fails = check(kept)
        log.append({"item_id": e["item_id"], "condition": e["condition"], "repeat": k, "attempt": a,
                    "raw_chars": len(raw), "cut_at": why, "kept_chars": len(kept), "valid": not fails,
                    "fail_reasons": " | ".join(fails)})
        if not fails:
            s4 = kept
            break
    if s4 is None:
        return None, None
    user5 = flatten(build_messages(p, c, step3_text=e["edited_step3"], step4_text=s4))
    found = MARK.findall(user5)
    if found != EXPECTED or "END OF STEP 4" in user5:
        raise AssertionError(f"Step 5 input for {e['item_id']} {e['condition']} r{k} has invented turn markers: {found}")
    return s4, judge(user5, f"{base(e['condition'], e['item_id'], k)}__step5")


def main():
    pilot = "--pilot" in sys.argv
    targets = [r["item_id"] for r in csv.DictReader(open(os.path.join(HERE, "items.csv"))) if r["group"] == "target"]
    if pilot:
        targets = targets[:2]
    reps = [0] if pilot else range(N_REPEATS)
    edits = sorted((e for e in csv.DictReader(open(os.path.join(HERE, "step3_edits.csv")))
                    if e["item_id"] in targets and e["condition"] in CONDS),
                   key=lambda e: (targets.index(e["item_id"]), CONDS.index(e["condition"])))
    planned = len(edits) * len(reps) * 2
    print(f"{'PILOT' if pilot else 'FULL'}: planned calls without retries: {planned} ({len(edits)} edits x "
          f"{len(reps)} repeats x 2 steps); follow-up calls already cached: {n_total()}; cap on all follow-up "
          f"calls incl. retries: {MAX_TOTAL}", flush=True)
    if planned > MAX_TOTAL:
        sys.exit("Refusing to start: planned calls exceed the cap.")
    log, out = [], []
    try:
        for e in edits:
            for k in reps:
                s4, s5 = run_repeat(e, k, log)
                sc = parse_score(s5) if s5 else None
                if s4 is None:
                    print(f"DROPPED {e['item_id']} {e['condition']} r{k}: Step 4 failed {MAX_ATTEMPTS} attempts", flush=True)
                elif sc is None:
                    print(f"PARSE FAILURE {e['item_id']} {e['condition']} r{k}: {s5[-200:]!r}", flush=True)
                n_att = sum(1 for r in log if r["item_id"] == e["item_id"] and r["condition"] == e["condition"]
                            and r["repeat"] == k)
                print(f"{e['item_id']} {e['condition']} r{k}: step4 attempts {n_att}, "
                      f"{'dropped' if s4 is None else f'{len(s4)} chars'} -> score {sc}", flush=True)
                out.append((e, k, s4, sc))
    except UsageLimit as err:
        print(f"Usage limit reached; rerun to resume from the cache. ({err})", flush=True)
    except CapReached as err:
        print(f"Stopped: {err}.", flush=True)
    finally:
        if log:
            name = "step4_attempts_pilot.csv" if pilot else "step4_attempts.csv"
            with open(os.path.join(HERE, name), "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(log[0]))
                w.writeheader()
                w.writerows(log)
        print(f"Follow-up calls in cache now: {n_total()}", flush=True)
    if pilot:
        md = ["# Pilot: regenerated Step 4 texts (after cut)\n"]
        for e, k, s4, sc in out:
            rows = [r for r in log if r["item_id"] == e["item_id"] and r["condition"] == e["condition"] and r["repeat"] == k]
            md.append(f"\n## {e['item_id']} — {e['condition']} r{k} — Step 5 score {sc}\n\n")
            for r in rows:
                md.append(f"- attempt {r['attempt']}: raw {r['raw_chars']} chars, cut at {r['cut_at']}, kept "
                          f"{r['kept_chars']} chars, valid={r['valid']} {r['fail_reasons']}\n")
            md.append("\n```\n" + (s4 or "(no valid Step 4)") + "\n```\n")
        open(os.path.join(HERE, "pilot_step4.md"), "w").write("".join(md))
        print("wrote pilot_step4.md")


if __name__ == "__main__":
    main()
