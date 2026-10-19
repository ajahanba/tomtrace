#!/usr/bin/env python3
"""
Analysis of the Step-3 counterfactual (reads cached calls in raw/).

PRIMARY: within-item difference between the edit condition and the same item's
  PARAPHRASE condition, each averaged over repeats:
    targets : to_within  - paraphrase
    reverse : to_contrast - paraphrase
  Mean over items with a bootstrap 95% CI over items. Anchoring on the paraphrase
  cancels any systematic offset between CLI reruns and the stored chains.
  Exact two-sided Wilcoxon signed-rank p over the item-level differences
  (zero differences dropped, Wilcoxon's method; tied |d| get average ranks; the null
  distribution is enumerated over all 2^n sign assignments).
FOLLOW-UP (targets only): the same comparison when Step 4 is regenerated too
  (Step 4 on the edited Step 3, Step 5 on the new Step 4); cache keys s45_*.
FLIPS: delta prediction (mean score >= 7) under the edit vs under the paraphrase,
  per item.
SECONDARY: shifts of each condition relative to the stored score.
NOISE: rerun SD (pooled within-item) and offset from stored, from the noise items.

Parse failures are logged and excluded, never imputed.
Outputs: results.md, results_items.csv, results_figure.svg
"""

import csv
import json
import os
import random
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from reconstruct import original, parse_score   # noqa: E402

RAW = os.path.join(HERE, "raw")
N_BOOT = 10000
SEED = 20261012
MAX_REPEATS = 20


def scores(prefix, item, suffix=""):
    p, c, _ = item.split("|")
    out, fails = [], 0
    for k in range(MAX_REPEATS):           # a dropped repeat leaves a gap; later repeats still count
        path = os.path.join(RAW, f"{prefix}__{p}_{c}__r{k}{suffix}.json")
        if not os.path.exists(path):
            continue
        s = parse_score(json.load(open(path))["output_text"])
        if s is None:
            fails += 1
        else:
            out.append(s)
    return out, fails


def boot_ci(vals):
    rng = random.Random(SEED)
    ms = sorted(st.mean(rng.choice(vals) for _ in vals) for _ in range(N_BOOT))
    return ms[int(0.025 * N_BOOT)], ms[int(0.975 * N_BOOT) - 1]


def wilcoxon_exact(vals):
    """Exact two-sided Wilcoxon signed-rank test. Returns (p, n_nonzero, W+)."""
    d = [v for v in vals if abs(v) > 1e-12]
    n = len(d)
    if n == 0:
        return 1.0, 0, 0.0
    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(abs(d[order[j + 1]]) - abs(d[order[i]])) < 1e-12:
            j += 1
        for t in range(i, j + 1):
            ranks[order[t]] = (i + j) / 2 + 1
        i = j + 1
    w_obs = sum(r for r, v in zip(ranks, d) if v > 0)
    centre = n * (n + 1) / 4
    dev = abs(w_obs - centre)
    hits = 0
    for mask in range(2 ** n):
        w = sum(ranks[b] for b in range(n) if mask >> b & 1)
        hits += abs(w - centre) >= dev - 1e-9
    return hits / 2 ** n, n, w_obs


def summarise(g, direction):
    """Primary-analysis lines for a list of item rows with diff/edit_mean/flip."""
    d = [r["diff"] for r in g]
    lo, hi = boot_ci(d)
    p, nz, w = wilcoxon_exact(d)
    flips = [r for r in g if r["flip"]]
    want = [r for r in flips if (direction == "up" and r["edit_mean"] >= 7) or
            (direction == "down" and r["edit_mean"] < 7)]
    return (f"- **Primary:** mean within-item difference {st.mean(d):+.2f} points "
            f"(bootstrap 95% CI {lo:+.2f} to {hi:+.2f}).\n"
            f"- **Exact Wilcoxon signed-rank:** two-sided p = {p:.4f} (W+ = {w:g}, n = {nz} non-zero "
            f"differences of {len(d)}; smallest attainable p with n = {nz} is {2 / 2 ** nz:.4f}).\n"
            f"- **Delta-prediction flips vs paraphrase:** {len(flips)} of {len(g)} items "
            f"({len(want)} in the expected direction).\n"), st.mean(d), (lo, hi), p


def svg(rows):
    """Dot plot: paraphrase mean -> edit mean per item, targets and reverse controls."""
    W, H, top, left, right = 760, 60 + 26 * len(rows), 40, 230, 30
    x = lambda v: left + (v - 1) / 9 * (W - left - right)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="11">',
           f'<rect width="{W}" height="{H}" fill="white"/>']
    for v in range(1, 11):
        out.append(f'<line x1="{x(v):.1f}" y1="{top - 10}" x2="{x(v):.1f}" y2="{H - 20}" stroke="#ddd"/>'
                   f'<text x="{x(v):.1f}" y="{H - 6}" text-anchor="middle">{v}</text>')
    out.append(f'<line x1="{x(7):.1f}" y1="{top - 10}" x2="{x(7):.1f}" y2="{H - 20}" stroke="#999" stroke-dasharray="4 3"/>'
               f'<text x="{x(7) + 3:.1f}" y="{top - 14}" fill="#666">delta threshold (7)</text>')
    for i, r in enumerate(rows):
        y = top + 26 * i
        col = "#1f77b4" if r["group"] == "target" else "#d62728"
        out.append(f'<text x="{left - 8}" y="{y + 4}" text-anchor="end">{r["item_id"].split("|")[0]} ({r["group"]})</text>')
        if r["para_mean"] is not None and r["edit_mean"] is not None:
            out.append(f'<line x1="{x(r["para_mean"]):.1f}" y1="{y}" x2="{x(r["edit_mean"]):.1f}" y2="{y}" '
                       f'stroke="{col}" stroke-width="2"/>'
                       f'<circle cx="{x(r["para_mean"]):.1f}" cy="{y}" r="4" fill="white" stroke="{col}" stroke-width="2"/>'
                       f'<circle cx="{x(r["edit_mean"]):.1f}" cy="{y}" r="4" fill="{col}"/>')
        out.append(f'<text x="{x(r["stored"]):.1f}" y="{y + 4}" text-anchor="middle" fill="#888">×</text>')
    out.append(f'<text x="{left}" y="18">○ paraphrase mean   ● edit mean (blue: to_within, red: to_contrast)   × stored score</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    items = list(csv.DictReader(open(os.path.join(HERE, "items.csv"))))
    rows, fail_log = [], []
    for it in items:
        if it["group"] not in ("target", "reverse"):
            continue
        cond = "to_within" if it["group"] == "target" else "to_contrast"
        p, c, _ = it["item_id"].split("|")
        stored = original(p, c)["generated_score"]
        es, ef = scores(cond, it["item_id"])
        ps, pf = scores("paraphrase", it["item_id"])
        if ef or pf:
            fail_log.append(f"{it['item_id']}: {ef} parse failures ({cond}), {pf} (paraphrase)")
        em = st.mean(es) if es else None
        pm = st.mean(ps) if ps else None
        rows.append({"item_id": it["item_id"], "group": it["group"], "condition": cond, "stored": stored,
                     "edit_scores": es, "para_scores": ps, "edit_mean": em, "para_mean": pm,
                     "diff": (em - pm) if em is not None and pm is not None else None,
                     "flip": (None if em is None or pm is None else (pm >= 7) != (em >= 7)),
                     "edit_minus_stored": (em - stored) if em is not None else None,
                     "para_minus_stored": (pm - stored) if pm is not None else None})
    md = ["# Step-3 counterfactual: results\n\n"]
    primary = {}
    for grp, cond, direction in (("target", "to_within", "up"), ("reverse", "to_contrast", "down")):
        g = [r for r in rows if r["group"] == grp and r["diff"] is not None]
        md.append(f"## {grp.title()} items: {cond} − paraphrase (n = {len(g)} items)\n\n")
        if len(g) >= 2:
            lines, m, ci, _ = summarise(g, direction)
            primary[grp] = (m, ci)
            md.append(lines)
            md.append(f"- Secondary: edit − stored {st.mean(r['edit_minus_stored'] for r in g):+.2f}; "
                      f"paraphrase − stored {st.mean(r['para_minus_stored'] for r in g):+.2f}.\n\n")
        else:
            md.append("- Not enough completed items yet.\n\n")
        md.append("| Item | Stored | Paraphrase scores | Edit scores | Paraphrase mean | Edit mean | Diff | Flip |\n"
                  "|---|---|---|---|---|---|---|---|\n")
        for r in [r for r in rows if r["group"] == grp]:
            f = lambda v: "—" if v is None else f"{v:.2f}"
            diff = "—" if r["diff"] is None else f"{r['diff']:+.2f}"
            flip = "—" if r["flip"] is None else ("yes" if r["flip"] else "no")
            md.append(f"| {r['item_id']} | {r['stored']} | {' '.join(map(str, r['para_scores']))} | "
                      f"{' '.join(map(str, r['edit_scores']))} | {f(r['para_mean'])} | {f(r['edit_mean'])} | "
                      f"{diff} | {flip} |\n")
        md.append("\n")
    # follow-up: Step 4 regenerated as well (targets only)
    fu = []
    for it in items:
        if it["group"] != "target":
            continue
        p, c, _ = it["item_id"].split("|")
        es, ef = scores("s45_to_within", it["item_id"], "__step5")
        ps, pf = scores("s45_paraphrase", it["item_id"], "__step5")
        if ef or pf:
            fail_log.append(f"{it['item_id']} (Step 4 regenerated): {ef} parse failures (to_within), {pf} (paraphrase)")
        if es and ps:
            em, pm = st.mean(es), st.mean(ps)
            fu.append({"item_id": it["item_id"], "stored": original(p, c)["generated_score"], "edit_scores": es,
                       "para_scores": ps, "edit_mean": em, "para_mean": pm, "diff": em - pm,
                       "flip": (pm >= 7) != (em >= 7)})
    if fu:
        md.append(f"## Follow-up, targets with Step 4 regenerated: to_within − paraphrase (n = {len(fu)} items)\n\n"
                  "Step 4 is regenerated on the edited (or paraphrased) Step 3 and Step 5 on that new Step 4; "
                  "repeat k of Step 5 uses repeat k of Step 4.\n\n")
        if len(fu) >= 2:
            lines, m, ci, _ = summarise(fu, "up")
            md.append(lines)
            if "target" in primary:
                m0, ci0 = primary["target"]
                md.append(f"- **Comparison with Step 4 fixed:** {m0:+.2f} (CI {ci0[0]:+.2f} to {ci0[1]:+.2f}) "
                          f"with Step 4 fixed vs {m:+.2f} (CI {ci[0]:+.2f} to {ci[1]:+.2f}) with Step 4 regenerated; "
                          f"difference {m - m0:+.2f}.\n")
            md.append("\n")
        att_path = os.path.join(HERE, "step4_attempts.csv")
        if os.path.exists(att_path):
            att = list(csv.DictReader(open(att_path)))
            md.append("| Condition | Repeats attempted | Step 4 attempts | Retries | Dropped repeats | Failed checks (count; an attempt can fail several) |\n"
                      "|---|---|---|---|---|---|\n")
            for cond in ("to_within", "paraphrase"):
                a = [r for r in att if r["condition"] == cond]
                reps = {(r["item_id"], r["repeat"]) for r in a}
                dropped = [k for k in reps if not any(r["valid"] == "True" for r in a
                                                      if (r["item_id"], r["repeat"]) == k)]
                cats = {}
                for r in a:
                    for f in filter(None, r["fail_reasons"].split(" | ")):
                        cat = f.split(":")[0].split(" ")[0] if f.startswith("length") else f.split(":")[0]
                        cats[cat] = cats.get(cat, 0) + 1
                reasons = [f"{c} {n}" for c, n in sorted(cats.items())]
                md.append(f"| {cond} | {len(reps)} | {len(a)} | {len(a) - len(reps)} | {len(dropped)}"
                          f"{' (' + ', '.join(f'{i.split(chr(124))[0]} r{k}' for i, k in sorted(dropped)) + ')' if dropped else ''}"
                          f" | {', '.join(reasons) or '—'} |\n")
            md.append("\n")
        fixed = {r["item_id"]: r for r in rows if r["group"] == "target"}
        md.append("| Item | Stored | Paraphrase scores | Edit scores | Paraphrase mean | Edit mean | Diff | "
                  "Diff (Step 4 fixed) | Flip |\n|---|---|---|---|---|---|---|---|---|\n")
        for r in fu:
            d0 = fixed.get(r["item_id"], {}).get("diff")
            md.append(f"| {r['item_id']} | {r['stored']} | {' '.join(map(str, r['para_scores']))} | "
                      f"{' '.join(map(str, r['edit_scores']))} | {r['para_mean']:.2f} | {r['edit_mean']:.2f} | "
                      f"{r['diff']:+.2f} | {'—' if d0 is None else f'{d0:+.2f}'} | {'yes' if r['flip'] else 'no'} |\n")
        md.append("\n")
    # noise baseline
    noise = [it for it in items if it["group"] == "noise"]
    sds, offs, nrows = [], [], []
    for it in noise:
        p, c, _ = it["item_id"].split("|")
        ss = []
        k = 0
        while os.path.exists(os.path.join(RAW, f"noise__{p}_{c}__orig__r{k}.json")):
            v = parse_score(json.load(open(os.path.join(RAW, f"noise__{p}_{c}__orig__r{k}.json")))["output_text"])
            if v is not None:
                ss.append(v)
            k += 1
        if len(ss) >= 2:
            sds.append(st.stdev(ss))
        if ss:
            offs.append(st.mean(ss) - original(p, c)["generated_score"])
        nrows.append((it["item_id"], original(p, c)["generated_score"], ss))
    md.append("## Noise and fidelity baseline (unedited reruns)\n\n")
    if sds:
        md.append(f"- Pooled within-item rerun SD: {st.mean(sds):.2f} points (n = {len(sds)} items).\n"
                  f"- Mean offset of rerun mean from stored score: {st.mean(offs):+.2f} points.\n\n")
    md.append("| Item | Stored | Rerun scores |\n|---|---|---|\n")
    for iid, stv, ss in nrows:
        md.append(f"| {iid} | {stv} | {' '.join(map(str, ss))} |\n")
    if fail_log:
        md.append("\n## Parse failures (excluded)\n\n" + "".join(f"- {x}\n" for x in fail_log))
    open(os.path.join(HERE, "results.md"), "w").write("".join(md))
    with open(os.path.join(HERE, "results_items.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["item_id", "group", "condition", "stored", "para_mean", "edit_mean",
                                           "diff", "flip", "edit_minus_stored", "para_minus_stored",
                                           "para_scores", "edit_scores"])
        w.writeheader()
        for r in rows:
            w.writerow({**{k: r[k] for k in w.fieldnames if k not in ("para_scores", "edit_scores")},
                        "para_scores": " ".join(map(str, r["para_scores"])),
                        "edit_scores": " ".join(map(str, r["edit_scores"]))})
    open(os.path.join(HERE, "results_figure.svg"), "w").write(svg(rows))
    print("".join(md))


if __name__ == "__main__":
    main()
