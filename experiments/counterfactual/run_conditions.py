#!/usr/bin/env python3
"""
Phase 3: re-generate Step 5 for every edited Step 3 (to_within, to_contrast,
paraphrase), N_REPEATS each, through the CLI. Steps 1, 2 and 4 are the stored
outputs; Step 3 is the edited text from step3_edits.csv.

Prints the planned call count first and refuses to start if it exceeds MAX_CALLS.
Resumes from raw/ cache; stops cleanly on a usage limit.
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from reconstruct import build_messages, C, parse_score     # noqa: E402
from cli_judge import call_judge, flatten, UsageLimit, RAW  # noqa: E402

N_REPEATS = 5
MAX_CALLS = 200


def key(cond, item, k):
    p, c, _ = item.split("|")
    return f"{cond}__{p}_{c}__r{k}"


def main():
    edits = list(csv.DictReader(open(os.path.join(HERE, "step3_edits.csv"))))
    planned = [(e, k) for e in edits for k in range(N_REPEATS)]
    pending = [(e, k) for e, k in planned
               if not os.path.exists(os.path.join(RAW, key(e["condition"], e["item_id"], k) + ".json"))]
    print(f"Planned edited-condition calls: {len(planned)} ({len(edits)} edits x {N_REPEATS}); "
          f"already cached: {len(planned) - len(pending)}; to run now: {len(pending)}", flush=True)
    if len(planned) > MAX_CALLS:
        sys.exit(f"Refusing to start: {len(planned)} calls exceeds the cap of {MAX_CALLS}.")
    done = 0
    for e, k in pending:
        p, c, _ = e["item_id"].split("|")
        user = flatten(build_messages(p, c, step3_text=e["edited_step3"]))
        try:
            text, _ = call_judge(C._SYSTEM, user, key(e["condition"], e["item_id"], k))
        except UsageLimit as err:
            print(f"Usage limit reached after {done} new calls; rerun to resume. ({err})", flush=True)
            return
        done += 1
        s = parse_score(text)
        if s is None:
            print(f"PARSE FAILURE {e['item_id']} {e['condition']} r{k}: {text[-200:]!r}", flush=True)
        print(f"[{done}/{len(pending)}] {e['item_id']} {e['condition']} r{k} -> {s}", flush=True)
    print("All edited-condition calls complete.")


if __name__ == "__main__":
    main()
