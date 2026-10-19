#!/usr/bin/env python3
"""
Who detects human-flagged failures?  AUC (with bootstrap 95% CI) of candidate
detectors against two human targets:
  any_failure : chain has >=1 annotator note coding a reasoning failure (19/50)
  hedging     : chain has >=1 note coded E1 (latitude hedging)       (8/50)

Detector directions are fixed in advance (higher value = predicted failure):
  judge score (low), PRISM (low), L (high), SC (low), CG (low),
  Step-3 text, zones: number of distinct latitude zones named (high),
  Step-3 text, hedges: hedge words per 100 words (high).
"""

import json
import os
import random
import re

import patom_bench_analysis as P

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20261007
N_BOOT = 5000

ZONES = {
    "assimilation": re.compile(r"assimilat", re.I),
    "contrast": re.compile(r"\bcontrast", re.I),
    "within": re.compile(r"within (the )?(op'?s?|their|his|her)?\s*(likely )?(latitude|acceptance|zone)", re.I),
}
HEDGES = re.compile(r"\b(might|may|could|perhaps|possibly|likely|probably|partially|partial|somewhat|"
                    r"risks?|edge|borderline|though|however|unclear|mixed)\b", re.I)


def auc(scores, labels):
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def auc_ci(scores, labels):
    rng = random.Random(SEED)
    idx = list(range(len(scores)))
    vals = []
    for _ in range(N_BOOT):
        s = [rng.choice(idx) for _ in idx]
        v = auc([scores[i] for i in s], [labels[i] for i in s])
        if v == v:
            vals.append(v)
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def main():
    items, _, _ = P.load_items([P.DEFAULT_DATA])
    meta = P.load_patom_metrics(P.DEFAULT_PATOM, "chain")
    notes = P.extract_notes(items)
    top = {f: ("2" if "rating" in f else ("No" if f == "s5_newreason" else "Yes")) for f in P.FIELD}

    def step3(it):
        return it["raw"]["Step 3 — Latitude of Acceptance"]

    det = {
        "Judge score": lambda it: -meta[it["key"]]["patom_score"],
        "PRISM": lambda it: -meta[it["key"]]["PRISM"],
        "L (= SC signal)": lambda it: meta[it["key"]]["L"],
        "CG": lambda it: -meta[it["key"]]["CG"],
        "Step-3 zones named": lambda it: sum(bool(rx.search(step3(it))) for rx in ZONES.values()),
        "Step-3 hedge rate": lambda it: 100 * len(HEDGES.findall(step3(it))) / max(1, len(step3(it).split())),
    }
    targets = {
        "any_failure": [any(n["item"] is it and n["code"] != "OT" for n in notes) for it in items],
        "hedging": [any(n["item"] is it and n["code"] == "E1" for n in notes) for it in items],
    }
    out = {}
    for t, lab in targets.items():
        out[t] = {"positives": sum(lab)}
        for name, f in det.items():
            sc = [f(it) for it in items]
            a = auc(sc, lab)
            lo, hi = auc_ci(sc, lab)
            out[t][name] = {"auc": a, "ci": [lo, hi]}
    json.dump(out, open(os.path.join(HERE, "tomtrace_detector_results.json"), "w"), indent=1)
    for t, d in out.items():
        print(f"== {t} (positives {d['positives']})")
        for k, v in d.items():
            if k != "positives":
                print(f"  {k:22s} AUC {v['auc']:.2f} [{v['ci'][0]:.2f}, {v['ci'][1]:.2f}]")


if __name__ == "__main__":
    main()
