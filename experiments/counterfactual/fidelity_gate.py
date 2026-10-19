#!/usr/bin/env python3
"""
Fidelity gate: re-generate Step 5 for the NOISE items with the ORIGINAL Steps 1-4
(N_REPEATS each) through the CLI, and compare with the stored Step-5 outputs.
Writes fidelity_gate.csv and fidelity_gate.md. Resumes from raw/ cache.
"""

import csv
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from reconstruct import build_messages, original, parse_score, C   # noqa: E402
from cli_judge import call_judge, flatten, UsageLimit, cli_version, MODEL  # noqa: E402

N_REPEATS = 5
FORMAT_RX = re.compile(r"^\s*Reasoning:\s*\S.*?\n?\s*Score:\s*\*{0,2}\s*\d{1,2}\s*\*{0,2}\s*$", re.S | re.I)


def main():
    items = [r for r in csv.DictReader(open(os.path.join(HERE, "items.csv"))) if r["group"] == "noise"]
    rows, done, stopped = [], 0, None
    for it in items:
        p, c, _ = it["item_id"].split("|")
        user = flatten(build_messages(p, c))
        stored = original(p, c)
        stored_score = stored["generated_score"]
        reruns, fmt, parse_fail, models = [], [], 0, set()
        for k in range(N_REPEATS):
            try:
                text, meta = call_judge(C._SYSTEM, user, f"noise__{p}_{c}__orig__r{k}")
            except UsageLimit as e:
                stopped = str(e)
                break
            done += 1
            models.update(meta.get("reported_models", []))
            s = parse_score(text)
            if s is None:
                parse_fail += 1
                print(f"PARSE FAILURE {it['item_id']} r{k}: {text[-200:]!r}", flush=True)
            else:
                reruns.append(s)
            fmt.append(bool(FORMAT_RX.match(text)))
        if reruns:
            mad = st.mean(abs(s - stored_score) for s in reruns)
            within1 = sum(abs(s - stored_score) <= 1 for s in reruns) / len(reruns)
            agree = sum((s >= 7) == (stored_score >= 7) for s in reruns) / len(reruns)
        else:
            mad = within1 = agree = float("nan")
        rows.append({"item_id": it["item_id"], "stored_score": stored_score,
                     "rerun_scores": " ".join(map(str, reruns)), "n_reruns": len(reruns),
                     "parse_failures": parse_fail, "mean_abs_diff": f"{mad:.2f}",
                     "within_1": f"{within1:.2f}", "delta_agreement": f"{agree:.2f}",
                     "format_match": f"{sum(fmt)}/{len(fmt)}",
                     "stored_format_match": bool(FORMAT_RX.match(stored['raw_response'])),
                     "reported_models": ";".join(sorted(models))})
        print(rows[-1], flush=True)
        if stopped:
            break
    with open(os.path.join(HERE, "fidelity_gate.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    allr = [(int(r["stored_score"]), int(s)) for r in rows for s in r["rerun_scores"].split()]
    # Pre-set criteria (fixed before results; do not adjust):
    #   signed and absolute difference: reported
    #   within +/-1 of stored:                           target >= 70% of reruns
    #   delta agreement using per-item MEAN rerun score: target >= 80% of items
    #   format: every output has a parseable score line (1-10)
    n_out = sum(int(r["n_reruns"]) + int(r["parse_failures"]) for r in rows)
    n_fail = sum(int(r["parse_failures"]) for r in rows)
    crit = {}
    if allr:
        signed = st.mean(b - a for a, b in allr)
        mad_all = st.mean(abs(b - a) for a, b in allr)
        within = sum(abs(b - a) <= 1 for a, b in allr) / len(allr)
        item_agree = [(st.mean(map(int, r["rerun_scores"].split())) >= 7) == (int(r["stored_score"]) >= 7)
                      for r in rows if r["rerun_scores"]]
        dagree = sum(item_agree) / len(item_agree)
        crit = {"mean signed difference (rerun - stored)": (f"{signed:+.2f}", "reported"),
                "mean absolute difference": (f"{mad_all:.2f}", "reported"),
                "share of reruns within +/-1 of stored (target >= 70%)": (f"{within:.0%}", "PASS" if within >= 0.70 else "FAIL"),
                "delta agreement, per-item mean rerun (target >= 80%)": (f"{dagree:.0%} ({sum(item_agree)}/{len(item_agree)} items)", "PASS" if dagree >= 0.80 else "FAIL"),
                "format: parseable score line in every output": (f"{n_out - n_fail}/{n_out}", "PASS" if n_fail == 0 else "FAIL")}
        summ = "; ".join(f"{k}: {v[0]} [{v[1]}]" for k, v in crit.items())
    else:
        summ = "No completed reruns."
    md = ["# Fidelity gate (NOISE items, original Steps 1-4)\n\n",
          f"CLI {cli_version()}, requested model `{MODEL}`, {N_REPEATS} repeats per item.\n\n",
          "## Pre-set criteria\n\n| Criterion | Value | Result |\n|---|---|---|\n",
          *[f"| {k} | {v[0]} | {v[1]} |\n" for k, v in crit.items()], "\n## Per item\n\n",
          "| Item | Stored | Reruns | MAD | Within ±1 | Δ agree | Format | Model(s) |\n",
          "|---|---|---|---|---|---|---|---|\n"]
    for r in rows:
        md.append(f"| {r['item_id']} | {r['stored_score']} | {r['rerun_scores']} | {r['mean_abs_diff']} | "
                  f"{r['within_1']} | {r['delta_agreement']} | {r['format_match']} | {r['reported_models']} |\n")
    if stopped:
        md.append(f"\n**Stopped early (usage limit):** {stopped}\n")
    open(os.path.join(HERE, "fidelity_gate.md"), "w").write("".join(md))
    print(summ, "| calls completed this run (incl. cached):", done, "| stopped:", bool(stopped))


if __name__ == "__main__":
    main()
