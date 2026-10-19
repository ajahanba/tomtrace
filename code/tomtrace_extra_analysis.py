#!/usr/bin/env python3
"""
Additional ToMTrace analyses for the WebConf revision (stdlib only).

  1. All 35 metric x label Spearman correlations with bootstrap 95% CIs,
     permutation p-values, and Benjamini-Hochberg FDR q-values.
  2. PRISM component analysis: leave-one-factor-out variants and rank-based
     partial correlations (PRISM | CG, CG | PRISM).
  3. Failure-note diagnostics: minority-only notes, notes normalised by chain
     length.
  4. Human spot-check of Qwen ToM profiles (repo data/annotations/annotations_user_*.json).
  5. LLM-as-annotator agreement with humans (if llm_annotations.json exists)
     and failure-coding reliability (rules vs LLM coder, if llm_note_codes.json exists).

Writes tomtrace_extra_results.json next to this file.
"""

import json
import math
import os
import random
from collections import Counter

import patom_bench_analysis as P

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "PaTom")
N_BOOT = 5000
N_PERM = 20000
SEED = 20261007

METRICS = [("L", "L"), ("rho", "rho"), ("SC", "SC"), ("CG", "CG"), ("CC", "CC"),
           ("PRISM", "PRISM"), ("patom_score", "Score")]
LABELS = ["s3_correct", "s3_rating", "s5_follows", "s5_rating", "chain"]


def mean_code(it, fid):
    if fid == "chain":
        return sum(mean_code(it, f"s{k}_rating") for k in range(1, 6))
    return sum(P.ORDINAL_MAP[P.get_label(it, a, fid)] for a in P.ANNOTATORS) / 3.0


def spearman_rho(x, y):
    return P.pearson(P.rankdata(list(x)), P.rankdata(list(y)))


def boot_ci(x, y, rng, stat=spearman_rho, n=N_BOOT):
    """Item bootstrap. Each call reseeds, so a statistic always gets the same CI
    regardless of how many other analyses ran before it."""
    rng = random.Random(SEED)
    idx = list(range(len(x)))
    vals = []
    for _ in range(n):
        s = [rng.choice(idx) for _ in idx]
        v = stat([x[i] for i in s], [y[i] for i in s])
        if not P.isnan(v):
            vals.append(v)
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def bh(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank, i in reversed(list(enumerate(order, 1))):
        prev = min(prev, pvals[i] * m / rank)
        q[i] = prev
    return q


def residual_ranks(y, x):
    """Residuals of rank(y) regressed on rank(x)."""
    ry, rx = P.rankdata(y), P.rankdata(x)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    b = sum((a - mx) * (c - my) for a, c in zip(rx, ry)) / sum((a - mx) ** 2 for a in rx)
    return [c - my - b * (a - mx) for a, c in zip(rx, ry)]


def partial_spearman(x, y, z):
    return P.pearson(residual_ranks(x, z), residual_ranks(y, z))


def perm_p(x, y, stat, rng, n=N_PERM):
    obs = stat(x, y)
    yp = list(y)
    ge = 0
    for _ in range(n):
        rng.shuffle(yp)
        if abs(stat(x, yp)) >= abs(obs) - 1e-12:
            ge += 1
    return obs, (ge + 1) / (n + 1)


def kappa(a, b, labels):
    return P.cohen_kappa(a, b, labels)


def main():
    rng = random.Random(SEED)
    items, _, _ = P.load_items([P.DEFAULT_DATA])
    meta = P.load_patom_metrics(P.DEFAULT_PATOM, "chain")
    for it in items:
        it["meta"] = meta[it["key"]]
    out = {}

    # ---------------------------------------------------------------- 1
    cells = []
    for col, name in METRICS:
        mv = [it["meta"][col] for it in items]
        for lab in LABELS:
            hv = [mean_code(it, lab) for it in items]
            r = P.spearman(hv, mv, rng, N_PERM)
            lo, hi = boot_ci(hv, mv, rng)
            cells.append({"metric": name, "label": lab, "rho": r["rho"], "p": r["p"],
                          "ci": [lo, hi]})
    for c, q in zip(cells, bh([c["p"] for c in cells])):
        c["q"] = q
    out["correlations"] = cells

    # ---------------------------------------------------------------- 2
    h3 = [mean_code(it, "s3_correct") for it in items]
    g = lambda it, k: it["meta"][k]
    variants = {
        "PRISM": lambda it: g(it, "L") * -g(it, "rho") * g(it, "SC") * math.sqrt(g(it, "CG") * g(it, "CC")),
        "PRISM without L": lambda it: -g(it, "rho") * g(it, "SC") * math.sqrt(g(it, "CG") * g(it, "CC")),
        "PRISM without -rho": lambda it: g(it, "L") * g(it, "SC") * math.sqrt(g(it, "CG") * g(it, "CC")),
        "PRISM without SC": lambda it: g(it, "L") * -g(it, "rho") * math.sqrt(g(it, "CG") * g(it, "CC")),
        "PRISM without sqrt(CG*CC)": lambda it: g(it, "L") * -g(it, "rho") * g(it, "SC"),
        "SC * sqrt(CG*CC)": lambda it: g(it, "SC") * math.sqrt(g(it, "CG") * g(it, "CC")),
    }
    abl = []
    for name, f in variants.items():
        v = [f(it) for it in items]
        rho, p = perm_p(h3, v, spearman_rho, rng)
        lo, hi = boot_ci(h3, v, rng)
        abl.append({"variant": name, "rho": rho, "p": p, "ci": [lo, hi]})
    out["prism_ablation"] = abl
    prism = [it["meta"]["PRISM"] for it in items]
    cg = [it["meta"]["CG"] for it in items]
    L = [it["meta"]["L"] for it in items]
    part = {}
    for name, x, z in [("PRISM | CG", prism, cg), ("CG | PRISM", cg, prism),
                       ("PRISM | L", prism, L), ("L | PRISM", L, prism)]:
        st = lambda a, b, z=z: partial_spearman(a, b, z)
        rho, p = perm_p(x, h3, st, rng)
        part[name] = {"rho": rho, "p": p}
    out["partial"] = part
    out["metric_intercorr"] = {
        f"{a}~{b}": spearman_rho([it["meta"][a] for it in items], [it["meta"][b] for it in items])
        for a, b in [("L", "SC"), ("L", "CG"), ("L", "PRISM"), ("CG", "PRISM"), ("SC", "PRISM")]}

    # ---------------------------------------------------------------- 3
    notes = P.extract_notes(items)
    fail_chains = {id(n["item"]) for n in notes if n["code"] != "OT"}
    below = [it for it in items
             if any(P.majority_vote(it, f"s{k}_rating")[0] != "2" for k in range(1, 6))]
    out["notes"] = {
        "n_notes": len(notes),
        "failure_notes": sum(n["code"] != "OT" for n in notes),
        "chains_with_failure_note": len(fail_chains),
        "chains_below_majority_correct": len(below),
        "failure_chains_below_majority": sum(id(it) in fail_chains for it in below),
        "failure_chains_all_majority_correct": len(fail_chains) - sum(id(it) in fail_chains for it in below),
    }
    steps = ["Step 1 — OP's Belief State", "Step 2 — Commenter's Argument",
             "Step 3 — Latitude of Acceptance", "Step 4 — Credibility & Tone",
             "Step 5 — Final Verdict"]
    by_model = {}
    for m in ("claude", "gpt5"):
        mi = [it for it in items if it["model"] == m]
        words = sum(len(it["raw"][s].split()) for it in mi for s in steps)
        nn = sum(1 for n in notes if n["item"]["model"] == m)
        nf = sum(1 for n in notes if n["item"]["model"] == m and n["code"] != "OT")
        by_model[m] = {"chains": len(mi), "words_per_chain": words / len(mi), "notes": nn,
                       "failure_notes": nf, "notes_per_chain": nn / len(mi),
                       "notes_per_1k_words": 1000 * nn / words,
                       "failure_notes_per_1k_words": 1000 * nf / words}
    out["length_norm"] = by_model
    out["rules"] = {k: v.pattern for k, v in P.RX.items()}

    # ---------------------------------------------------------------- 4
    try:
        A = [json.load(open(os.path.join(REPO, "data", "annotations", f"annotations_user_{u}.json")))
             for u in (2, 6)]
        qs = ["q2_beliefs", "q3_desires", "q4_intentions", "q5_emotions", "q6_knowledge",
              "q7_perspective_taking"]
        ids = [{x["persuasive_comment"]["id"]: x for x in a} for a in A]
        common = sorted(set(ids[0]) & set(ids[1]))
        spot = {"items": len(common), "fields": {}}
        for q in qs:
            ys = [sum(ids[k][c]["annotation"][q] == "Y" for c in common) for k in (0, 1)]
            both = sum(all(ids[k][c]["annotation"][q] == "Y" for k in (0, 1)) for c in common)
            agree = sum(ids[0][c]["annotation"][q] == ids[1][c]["annotation"][q] for c in common)
            spot["fields"][q] = {"yes": ys, "both_yes": both, "agree": agree}
        spot["valid_rate"] = [sum(ids[k][c]["annotation"][q] == "Y" for c in common for q in qs)
                              / (len(common) * len(qs)) for k in (0, 1)]
        out["qwen_spotcheck"] = spot
    except FileNotFoundError:
        pass

    # ---------------------------------------------------------------- 5
    llm_path = os.path.join(HERE, "llm_annotations.json")
    if os.path.exists(llm_path):
        llm = json.load(open(llm_path))
        res = {"model": llm.get("model"), "fields": {}}
        for fid, f in P.FIELD.items():
            labels = f[3]
            rows = [(it, llm["items"].get("|".join(it["key"]), {}).get(fid)) for it in items]
            rows = [(it, v) for it, v in rows if v is not None]
            maj = [(P.majority_vote(it, fid)[0], v) for it, v in rows]
            maj = [(a, b) for a, b in maj if a is not None]
            acc_maj = sum(a == b for a, b in maj) / len(maj)
            k_h = [kappa([P.get_label(it, a, fid) for it, _ in rows], [v for _, v in rows], labels)
                   for a in P.ANNOTATORS]
            # human leave-one-out: each annotator vs majority of the other two (when they agree)
            loo = []
            llm_loo = []
            for it, v in rows:
                labs = {a: P.get_label(it, a, fid) for a in P.ANNOTATORS}
                for a in P.ANNOTATORS:
                    o = [labs[b] for b in P.ANNOTATORS if b != a]
                    if o[0] == o[1]:
                        loo.append(labs[a] == o[0])
                        llm_loo.append(v == o[0])
            units4 = [[P.get_label(it, a, fid) for a in P.ANNOTATORS] + [v] for it, v in rows]
            units3 = [[P.get_label(it, a, fid) for a in P.ANNOTATORS] for it, _ in rows]
            res["fields"][fid] = {
                "n": len(rows), "llm_vs_majority": acc_maj,
                "kappa_llm_vs_each_human": k_h,
                "human_loo_acc": sum(loo) / len(loo), "llm_loo_acc": sum(llm_loo) / len(llm_loo),
                "ac1_humans": P.gwet_ac1(units3, labels), "ac1_humans_plus_llm": P.gwet_ac1(units4, labels),
                "llm_dist": dict(Counter(v for _, v in rows)),
            }
        out["llm_baseline"] = res
    codes_path = os.path.join(HERE, "llm_note_codes.json")
    if os.path.exists(codes_path):
        lc = json.load(open(codes_path))["codes"]
        pairs = [(n["code"], lc.get(f"{n['item']['post_id']}|{n['item']['model']}|{n['annotator']}|{n['step']}"))
                 for n in notes]
        pairs = [(a, b) for a, b in pairs if b]
        labs = sorted({a for a, _ in pairs} | {b for _, b in pairs})
        out["coding_reliability"] = {"n": len(pairs),
                                     "agreement": sum(a == b for a, b in pairs) / len(pairs),
                                     "kappa": kappa([a for a, _ in pairs], [b for _, b in pairs], labs),
                                     "confusions": Counter(f"{a}->{b}" for a, b in pairs if a != b).most_common(8)}

    json.dump(out, open(os.path.join(HERE, "tomtrace_extra_results.json"), "w"), indent=1, default=str)
    print(json.dumps({k: (v if k not in ("correlations", "rules") else "...") for k, v in out.items()},
                     indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
