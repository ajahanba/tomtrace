#!/usr/bin/env python3
"""
(1) Dawid-Skene model of Step-3 classification-correctness labels: annotator
    reliability (confusion matrices) and per-item difficulty (posterior entropy).
(2) Comment strategies (comment_strategies.json, LLM-tagged) vs. annotator
    disagreement, judge off-latitude calls, and item difficulty.
Output: tomtrace_ds_results.json
"""

import json
import math
import os

import patom_bench_analysis as P

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = ["Yes", "Partially", "No"]
STRATS = ["concession", "reframe", "new_evidence", "personal_experience", "direct_rebuttal", "tone_sharp"]


def dawid_skene(data, labels, iters=200):
    """data: list of {annotator: label}. Returns (class priors, confusion, posteriors)."""
    K = len(labels)
    li = {l: i for i, l in enumerate(labels)}
    anns = sorted({a for d in data for a in d})
    # init posteriors with soft majority vote
    T = []
    for d in data:
        c = [0.01] * K
        for l in d.values():
            c[li[l]] += 1
        s = sum(c)
        T.append([x / s for x in c])
    for _ in range(iters):
        pri = [sum(t[k] for t in T) / len(T) for k in range(K)]
        conf = {}
        for a in anns:
            m = [[0.01] * K for _ in range(K)]
            for t, d in zip(T, data):
                if a in d:
                    for k in range(K):
                        m[k][li[d[a]]] += t[k]
            conf[a] = [[x / sum(row) for x in row] for row in m]
        newT = []
        for d in data:
            p = [math.log(pri[k]) + sum(math.log(conf[a][k][li[l]]) for a, l in d.items()) for k in range(K)]
            mx = max(p)
            e = [math.exp(x - mx) for x in p]
            s = sum(e)
            newT.append([x / s for x in e])
        T = newT
    return pri, conf, T


def entropy(p):
    return -sum(x * math.log(x, 2) for x in p if x > 0)


def mannwhitney_auc(x_pos, x_neg):
    w = sum((a > b) + 0.5 * (a == b) for a in x_pos for b in x_neg)
    return w / (len(x_pos) * len(x_neg))


def main():
    items, _, _ = P.load_items([P.DEFAULT_DATA])
    data = [{a: P.get_label(it, a, "s3_correct") for a in P.ANNOTATORS} for it in items]
    pri, conf, T = dawid_skene(data, LABELS)
    out = {"priors": dict(zip(LABELS, pri)),
           "annotator_accuracy": {a: sum(pri[k] * conf[a][k][k] for k in range(3)) for a in conf},
           "annotator_confusion": conf}
    diff = [entropy(t) for t in T]
    out["difficulty"] = {"mean": sum(diff) / len(diff),
                         "n_hard": sum(d > 0.5 for d in diff),
                         "ds_vs_majority_disagree": sum(
                             LABELS[max(range(3), key=lambda k: t[k])] != (P.majority_vote(it, "s3_correct")[0])
                             for t, it in zip(T, items))}
    # strategies (optional; requires comment_strategies.json, not part of the release)
    tpath = os.path.join(HERE, "comment_strategies.json")
    if not os.path.exists(tpath):
        json.dump(out, open(os.path.join(HERE, "tomtrace_ds_results.json"), "w"), indent=1)
        print(json.dumps(out, indent=1)[:2000])
        return
    tags = json.load(open(tpath))["tags"]
    rows = []
    for it, d in zip(items, diff):
        tg = tags["|".join(it["key"][:2])]
        rows.append({"tags": tg,
                     "disagree": len({P.get_label(it, a, "s3_correct") for a in P.ANNOTATORS}) > 1,
                     "offlat": P.majority_vote(it, "s3_class")[0] != "Within latitude",
                     "class_disagree": len({P.get_label(it, a, "s3_class") for a in P.ANNOTATORS}) > 1,
                     "difficulty": d})
    out["n_disagree"] = sum(r["disagree"] for r in rows)
    out["n_offlat"] = sum(r["offlat"] for r in rows)
    out["strategy_prevalence"] = {s: sum(r["tags"][s] for r in rows) for s in STRATS}
    out["cover_and_reframe"] = sum(r["tags"]["concession"] and r["tags"]["reframe"] for r in rows)
    res = {}
    pvals = []
    for s in STRATS + ["cover_and_reframe"]:
        has = (lambda r: r["tags"]["concession"] and r["tags"]["reframe"]) if s == "cover_and_reframe" \
            else (lambda r, s=s: r["tags"][s])
        res[s] = {}
        for outc in ("disagree", "offlat", "class_disagree"):
            a = sum(has(r) and r[outc] for r in rows)
            b = sum(has(r) and not r[outc] for r in rows)
            c = sum((not has(r)) and r[outc] for r in rows)
            d = sum((not has(r)) and not r[outc] for r in rows)
            p = P.fisher_exact_2x2(a, b, c, d)
            res[s][outc] = {"with": f"{a}/{a + b}", "without": f"{c}/{c + d}", "p": p}
            pvals.append(p)
        pos = [r["difficulty"] for r in rows if has(r)]
        neg = [r["difficulty"] for r in rows if not has(r)]
        res[s]["difficulty_auc"] = mannwhitney_auc(pos, neg) if pos and neg else None
    out["strategy_tests"] = res
    out["min_p"] = min(pvals)
    json.dump(out, open(os.path.join(HERE, "tomtrace_ds_results.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "annotator_confusion"}, indent=1))


if __name__ == "__main__":
    main()
