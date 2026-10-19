#!/usr/bin/env python3
"""
Cluster-robust inference for ToMTrace. The 50 chains come from 43 posts; the 7
(post, comment) pairs judged by both models share a cluster. All bootstrap CIs
resample posts (clusters), and permutation tests permute whole clusters, swapping
clusters only with clusters of the same size (36 singletons, 7 pairs).

Recomputes: the 35 metric x label correlations (CI, p, BH q), the PRISM ablation
and partial correlations, the detector AUCs, Krippendorff's alpha CI for the
Step-3a classification, and the encoder-robustness correlations. Also writes
per-item soft labels (annotator means, Dawid-Skene posteriors).

Output: tomtrace_cluster_results.json, soft_labels.json
"""

import json
import math
import os
import random
from collections import defaultdict

import patom_bench_analysis as P
import tomtrace_extra_analysis as X
import tomtrace_detectors as D
import tomtrace_ds_strategies as DS

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20261008
N_BOOT = 5000
N_PERM = 20000


def clusters(items):
    by = defaultdict(list)
    for i, it in enumerate(items):
        by[it["post_id"]].append(i)
    return list(by.values())


def cluster_boot(stat, arrays, cl, n=N_BOOT):
    rng = random.Random(SEED)
    vals = []
    for _ in range(n):
        idx = [i for c in (rng.choice(cl) for _ in cl) for i in c]
        v = stat(*[[a[i] for i in idx] for a in arrays])
        if v == v:
            vals.append(v)
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def cluster_perm(stat, x, y, cl, n=N_PERM):
    """Two-sided p: permute y across clusters of equal size, preserving within-cluster order."""
    rng = random.Random(SEED)
    obs = stat(x, y)
    groups = defaultdict(list)
    for c in cl:
        groups[len(c)].append(c)
    ge = 0
    for _ in range(n):
        yp = [None] * len(y)
        for size, cs in groups.items():
            perm = cs[:]
            rng.shuffle(perm)
            for src, dst in zip(cs, perm):
                for a, b in zip(src, dst):
                    yp[a] = y[b]
        if abs(stat(x, yp)) >= abs(obs) - 1e-12:
            ge += 1
    return obs, (ge + 1) / (n + 1)


def main():
    items, _, _ = P.load_items([P.DEFAULT_DATA])
    meta = P.load_patom_metrics(P.DEFAULT_PATOM, "chain")
    for it in items:
        it["meta"] = meta[it["key"]]
    cl = clusters(items)
    out = {"n_clusters": len(cl), "cluster_sizes": sorted({len(c) for c in cl})}
    rho = X.spearman_rho

    # 35 correlations
    cells = []
    for col, name in X.METRICS:
        mv = [it["meta"][col] for it in items]
        for lab in X.LABELS:
            hv = [X.mean_code(it, lab) for it in items]
            r, p = cluster_perm(rho, hv, mv, cl)
            lo, hi = cluster_boot(rho, [hv, mv], cl)
            cells.append({"metric": name, "label": lab, "rho": r, "p": p, "ci": [lo, hi]})
    for c, q in zip(cells, X.bh([c["p"] for c in cells])):
        c["q"] = q
    out["correlations"] = cells

    # ablation + partials
    h3 = [X.mean_code(it, "s3_correct") for it in items]
    g = lambda it, k: it["meta"][k]
    variants = {
        "PRISM": lambda it: g(it, "L") * -g(it, "rho") * g(it, "SC") * math.sqrt(g(it, "CG") * g(it, "CC")),
        "without L": lambda it: -g(it, "rho") * g(it, "SC") * math.sqrt(g(it, "CG") * g(it, "CC")),
        "without -rho": lambda it: g(it, "L") * g(it, "SC") * math.sqrt(g(it, "CG") * g(it, "CC")),
        "without SC": lambda it: g(it, "L") * -g(it, "rho") * math.sqrt(g(it, "CG") * g(it, "CC")),
        "without sqrt(CG*CC)": lambda it: g(it, "L") * -g(it, "rho") * g(it, "SC"),
    }
    out["ablation"] = {}
    for name, f in variants.items():
        v = [f(it) for it in items]
        r, p = cluster_perm(rho, h3, v, cl)
        out["ablation"][name] = {"rho": r, "p": p, "ci": list(cluster_boot(rho, [h3, v], cl))}
    prism = [g(it, "PRISM") for it in items]
    cg = [g(it, "CG") for it in items]
    for name, x, z in [("PRISM | CG", prism, cg), ("CG | PRISM", cg, prism)]:
        st = lambda a, b, z=z: X.partial_spearman(a, b, z)
        r, p = cluster_perm(st, x, h3, cl)
        out["ablation"][name] = {"rho": r, "p": p}

    # detectors (no LLM-based detector)
    notes = P.extract_notes(items)
    targets = {
        "any_failure": [any(n["item"] is it and n["code"] != "OT" for n in notes) for it in items],
        "hedging": [any(n["item"] is it and n["code"] == "E1" for n in notes) for it in items],
    }
    s3 = lambda it: it["raw"]["Step 3 — Latitude of Acceptance"]
    det = {
        "Judge score": lambda it: -g(it, "patom_score"),
        "PRISM": lambda it: -g(it, "PRISM"),
        "L": lambda it: g(it, "L"),
        "CG": lambda it: -g(it, "CG"),
        "Step-3 zones named": lambda it: sum(bool(rx.search(s3(it))) for rx in D.ZONES.values()),
        "Step-3 hedge rate": lambda it: 100 * len(D.HEDGES.findall(s3(it))) / max(1, len(s3(it).split())),
    }
    out["detectors"] = {}
    for t, lab in targets.items():
        out["detectors"][t] = {}
        for name, f in det.items():
            sc = [f(it) for it in items]
            out["detectors"][t][name] = {"auc": D.auc(sc, lab),
                                         "ci": list(cluster_boot(D.auc, [sc, lab], cl))}

    # alpha CI for classification identification (cluster bootstrap over units)
    units = [[P.get_label(it, a, "s3_class") for a in P.ANNOTATORS] for it in items]
    labels = P.FIELD["s3_class"][3]
    out["alpha_s3_class"] = {"alpha": P.krippendorff_alpha(units, labels),
                             "ci": list(cluster_boot(lambda u: P.krippendorff_alpha(u, labels), [units], cl))}

    # encoder robustness
    enc_path = os.path.join(HERE, "encoder_metrics.json")
    if os.path.exists(enc_path):
        E = json.load(open(enc_path))
        keys = ["|".join(it["key"]) for it in items]
        out["encoders"] = {}
        for enc, M in E.items():
            out["encoders"][enc] = {}
            for m in ["L", "SC", "CG", "CC", "PRISM"]:
                v = [M[k][m] for k in keys]
                r, p = cluster_perm(rho, h3, v, cl)
                out["encoders"][enc][m] = {"rho": r, "p": p}
            v = lambda m: [M[k][m] for k in keys]
            wol = [-M[k]["rho"] * M[k]["SC"] * math.sqrt(max(0, M[k]["CG"] * M[k]["CC"])) for k in keys]
            r, p = cluster_perm(rho, h3, wol, cl)
            out["encoders"][enc]["PRISM without L"] = {"rho": r, "p": p}
            for name, x, z in [("PRISM | CG", v("PRISM"), v("CG")), ("CG | PRISM", v("CG"), v("PRISM"))]:
                st = lambda a, b, z=z: X.partial_spearman(a, b, z)
                r, p = cluster_perm(st, x, h3, cl)
                out["encoders"][enc][name] = {"rho": r, "p": p}
            out["encoders"][enc]["L~SC"] = rho(v("L"), v("SC"))

    json.dump(out, open(os.path.join(HERE, "tomtrace_cluster_results.json"), "w"), indent=1)

    # soft labels
    data = [{a: P.get_label(it, a, "s3_correct") for a in P.ANNOTATORS} for it in items]
    _, _, T = DS.dawid_skene(data, DS.LABELS)
    soft = {}
    for it, t in zip(items, T):
        soft["|".join(it["key"])] = {
            "mean_codes": {f: X.mean_code(it, f) for f, spec in P.FIELD.items() if spec[4]},
            "s3_correct_dawid_skene": dict(zip(DS.LABELS, t)),
        }
    json.dump(soft, open(os.path.join(HERE, "soft_labels.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "correlations"}, indent=1, default=str)[:5000])
    print("min q", min(c["q"] for c in cells), "p<.05:", sum(c["p"] < 0.05 for c in cells))


if __name__ == "__main__":
    main()
