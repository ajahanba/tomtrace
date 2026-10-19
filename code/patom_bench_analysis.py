#!/usr/bin/env python3
"""
PAToM-Bench analysis pipeline (Appendix A "Analysis Plan", Phases 1-7).

Pure standard-library Python (no numpy/scipy needed).

Usage
-----
    python3 patom_bench_analysis.py                                   # defaults
    python3 patom_bench_analysis.py --data a.json b.json \
        --meta item_metadata.csv --out patom_bench_results.tex

Inputs
------
--data  One or more annotation exports (JSON list, one record per item, with
        an "annotations" list of {Annotator, steps{Step 1..Step 5}}).
        Multiple files are merged (Phase 1.1).
--patom-metrics  Per-sample metrics JSONL(s) from the PaTom repo
        (https://github.com/baktash81/PaTom, results/*metrics_per_sample.jsonl);
        default: patom_repo_metrics/*.jsonl. Rows of --condition (default "chain",
        the PAToM chain) supply comment_type, L, SC, PRISM, its components and score.
--meta  OPTIONAL CSV keyed by post_id, comment_id, model (overrides the above). Any of these columns
        are used when present:
            comment_type   P / H / E  (persuasive / hard-negative / easy-negative)
            L, delta3, SC, PRISM      trajectory metrics from the PAToM paper
            patom_score               PAToM final score
            agreed_wrong              1 if all models agreed & were wrong
        Analyses that need these fields are reported as "not computable" when
        the file / column is absent, so the script can be re-run unchanged
        once the full merged dataset is available.

Schema mapping (export -> paper schema)
---------------------------------------
The pilot export records, per annotator and step, a 0/1/2 quality `rating`
plus these categorical fields:
    Step 3  classification_used        Within latitude / Assimilation / Contrast
    Step 3  is_classification_correct  Yes / Partially / No
    Step 5  verdict_follows_directly   Yes / Partially / No
    Step 5  introduces_new_reasoning   Yes / No
We map:
    Step 3a accuracy (ordinal)  = is_classification_correct  Yes=2, Partially=1, No=0
                                  (paper: correct_targeting=2, underdetermined=1, error=0)
    Step 3a error type          = classification_used on items whose classification
                                  was NOT judged fully correct
    Step 5 grounding (ordinal)  = verdict_follows_directly   Yes=2, Partially=1, No=0
                                  (paper: chain_grounded=2, partially=1, ungrounded=0)
Step 3b (profile grounding) and Step 6 (chain holistic) are not in the export.
"""

import argparse
import csv
import itertools
import json
import math
import os
import random
import re
import sys
from collections import Counter, OrderedDict, defaultdict

SEED = 20260626
N_PERM = 20000
N_BOOT = 2000

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(HERE, "MSO222_PersuasionReasoningAnnotation_50.json")
DEFAULT_OUT = os.path.join(HERE, "patom_bench_results.tex")
DEFAULT_PATOM = [p for p in (os.path.join(HERE, "patom_repo_metrics", f) for f in
                 ("metrics_per_sample.jsonl", "qwen_metrics_per_sample.jsonl")) if os.path.exists(p)]

ANNOTATORS = ["A1", "A2", "A3"]
MODEL_NAMES = {"claude": "Claude Sonnet 4.6", "gpt5": "GPT-5", "qwen": "Qwen3-30B"}
KEY = ("post_id", "comment_id", "model")

# (field id, step, json field, label set in canonical order, is_ordinal, display name)
FIELDS = [
    ("s1_rating", "Step 1", "rating", ["0", "1", "2"], True, "Step 1 --- OP belief (rating)"),
    ("s2_rating", "Step 2", "rating", ["0", "1", "2"], True, "Step 2 --- Commenter (rating)"),
    ("s3_rating", "Step 3", "rating", ["0", "1", "2"], True, "Step 3 --- Latitude (rating)"),
    ("s3_class", "Step 3", "classification_used",
     ["Within latitude", "Assimilation", "Contrast"], False, "Step 3a --- Classification used"),
    ("s3_correct", "Step 3", "is_classification_correct",
     ["No", "Partially", "Yes"], True, "Step 3a --- Classification correct"),
    ("s4_rating", "Step 4", "rating", ["0", "1", "2"], True, "Step 4 --- Social mgmt (rating)"),
    ("s5_rating", "Step 5", "rating", ["0", "1", "2"], True, "Step 5 --- Verdict (rating)"),
    ("s5_follows", "Step 5", "verdict_follows_directly",
     ["No", "Partially", "Yes"], True, "Step 5 --- Verdict follows directly"),
    ("s5_newreason", "Step 5", "introduces_new_reasoning",
     ["No", "Yes"], False, "Step 5 --- Introduces new reasoning"),
]
FIELD = {f[0]: f for f in FIELDS}
ORDINAL_MAP = {"No": 0, "Partially": 1, "Yes": 2, "0": 0, "1": 1, "2": 2}

MISSING_PLAN_FIELDS = {
    "comment_type": "comment type (P/H/E)",
    "L": "arc length $L$",
    "delta3": "step-3 deflection $\\Delta_3$",
    "SC": "ROSCOE step coherence (SC)",
    "PRISM": "PRISM",
    "patom_score": "\\patom{} final score",
    "agreed_wrong": "agreed-wrong flag",
}


# =============================================================================
# Statistics (stdlib implementations)
# =============================================================================

def nan():
    return float("nan")


def isnan(x):
    return isinstance(x, float) and math.isnan(x)


def cohen_kappa(a, b, labels):
    n = len(a)
    if n == 0:
        return nan()
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[l] * cb[l] for l in labels) / (n * n)
    if abs(1 - pe) < 1e-12:
        return nan()  # both raters used a single identical category
    return (po - pe) / (1 - pe)


def krippendorff_alpha(units, labels, level="nominal"):
    """units: list of lists of values (one list per item, missing omitted)."""
    idx = {l: i for i, l in enumerate(labels)}
    k = len(labels)
    o = [[0.0] * k for _ in range(k)]
    for vals in units:
        m = len(vals)
        if m < 2:
            continue
        for i, j in itertools.permutations(range(m), 2):
            o[idx[vals[i]]][idx[vals[j]]] += 1.0 / (m - 1)
    nc = [sum(row) for row in o]
    n = sum(nc)
    if n <= 1:
        return nan()

    def delta2(c, kk):
        if c == kk:
            return 0.0
        if level == "nominal":
            return 1.0
        lo, hi = min(c, kk), max(c, kk)  # ordinal metric
        return (sum(nc[g] for g in range(lo, hi + 1)) - (nc[c] + nc[kk]) / 2.0) ** 2

    do = sum(o[c][kk] * delta2(c, kk) for c in range(k) for kk in range(k))
    de = sum(nc[c] * nc[kk] * delta2(c, kk) for c in range(k) for kk in range(k))
    if de == 0:
        return nan()
    return 1 - (n - 1) * do / de


def gwet_ac1(units, labels):
    """Multi-rater Gwet AC1 (robust to the high-prevalence kappa paradox)."""
    q = len(labels)
    items = [u for u in units if len(u) >= 2]
    if not items or q < 2:
        return nan()
    pa = 0.0
    tot = Counter()
    for u in items:
        c = Counter(u)
        r = len(u)
        pa += sum(c[l] * (c[l] - 1) for l in labels) / (r * (r - 1))
        for l in labels:
            tot[l] += c[l] / r
    pa /= len(items)
    pi = {l: tot[l] / len(items) for l in labels}
    pe = sum(pi[l] * (1 - pi[l]) for l in labels) / (q - 1)
    if abs(1 - pe) < 1e-12:
        return nan()
    return (pa - pe) / (1 - pe)


def exact3(units):
    items = [u for u in units if len(u) == 3]
    if not items:
        return nan()
    return sum(len(set(u)) == 1 for u in items) / len(items)


def bootstrap_ci(units, stat, rng, n_boot=N_BOOT):
    vals = []
    n = len(units)
    for _ in range(n_boot):
        s = [units[rng.randrange(n)] for _ in range(n)]
        v = stat(s)
        if not isnan(v):
            vals.append(v)
    if len(vals) < n_boot * 0.5:
        return (nan(), nan())
    vals.sort()
    return (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1])


def wilson(k, n, z=1.959964):
    if n == 0:
        return (nan(), nan())
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def binom_sf(k, n, p):
    """P(X >= k) for X ~ Bin(n, p)."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def fisher_exact_2x2(a, b, c, d):
    """Two-sided Fisher exact test for [[a, b], [c, d]]."""
    r1, r2, c1 = a + b, c + d, a + c
    n = r1 + r2

    def p(x):
        return math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)

    p0 = p(a)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= p0 * (1 + 1e-7)))


def _chi2_stat(rows, cols):
    rl, cl = sorted(set(rows)), sorted(set(cols))
    n = len(rows)
    obs = Counter(zip(rows, cols))
    rt, ct = Counter(rows), Counter(cols)
    s = 0.0
    for r in rl:
        for c in cl:
            e = rt[r] * ct[c] / n
            s += (obs[(r, c)] - e) ** 2 / e
    return s, (len(rl) - 1) * (len(cl) - 1)


def _gammainc_upper_reg(s, x):
    """Regularised upper incomplete gamma Q(s, x)."""
    if x <= 0:
        return 1.0
    if x < s + 1:  # series
        term = total = 1.0 / s
        a = s
        for _ in range(500):
            a += 1
            term *= x / a
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return 1.0 - total * math.exp(-x + s * math.log(x) - math.lgamma(s))
    b = x + 1 - s  # continued fraction (Lentz)
    c = 1e300
    d = 1 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - s)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d
        h *= d * c
        if abs(d * c - 1) < 1e-15:
            break
    return math.exp(-x + s * math.log(x) - math.lgamma(s)) * h


def chi2_test(rows, cols, rng, n_perm=N_PERM):
    """Pearson chi-square with asymptotic and Monte-Carlo permutation p-values."""
    if len(set(rows)) < 2 or len(set(cols)) < 2:
        return None
    stat, df = _chi2_stat(rows, cols)
    p_asym = _gammainc_upper_reg(df / 2.0, stat / 2.0)
    cols_perm = list(cols)
    ge = 0
    for _ in range(n_perm):
        rng.shuffle(cols_perm)
        if _chi2_stat(rows, cols_perm)[0] >= stat - 1e-9:
            ge += 1
    n = len(rows)
    cramer = math.sqrt(stat / (n * min(len(set(rows)) - 1, len(set(cols)) - 1)))
    return {"chi2": stat, "df": df, "p_asym": p_asym,
            "p_perm": (ge + 1) / (n_perm + 1), "V": cramer, "n": n}


def rankdata(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    ranks = [0.0] * len(x)
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2.0 + 1
        i = j + 1
    return ranks


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return nan()
    return sxy / math.sqrt(sxx * syy)


def spearman(x, y, rng, n_perm=N_PERM):
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None
             and not isnan(a) and not isnan(b)]
    if len(pairs) < 4:
        return None
    xs, ys = zip(*pairs)
    rx, ry = rankdata(list(xs)), rankdata(list(ys))
    rho = pearson(rx, ry)
    if isnan(rho):
        return {"rho": nan(), "p": nan(), "n": len(pairs)}
    ryp = list(ry)
    ge = 0
    for _ in range(n_perm):
        rng.shuffle(ryp)
        if abs(pearson(rx, ryp)) >= abs(rho) - 1e-12:
            ge += 1
    return {"rho": rho, "p": (ge + 1) / (n_perm + 1), "n": len(pairs)}


# =============================================================================
# Phase 1 --- data preparation
# =============================================================================

def load_items(paths):
    items, seen, dups, problems = [], {}, [], []
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            recs = json.load(fh)
        for r in recs:
            key = tuple(str(r.get(k, "")).strip() for k in KEY)
            if not all(key):
                problems.append(f"{os.path.basename(path)}: record missing key field {key}")
                continue
            if key in seen:
                dups.append((key, seen[key], os.path.basename(path)))
                continue
            seen[key] = os.path.basename(path)
            ann = {a["Annotator"]: a["steps"] for a in r.get("annotations", [])}
            missing = [a for a in ANNOTATORS if a not in ann]
            if missing:
                problems.append(f"{key}: missing annotators {missing}")
            for a, steps in ann.items():
                for f in FIELDS:
                    if f[2] not in steps.get(f[1], {}):
                        problems.append(f"{key} {a}: missing {f[1]}.{f[2]}")
            items.append({"key": key, "post_id": key[0], "comment_id": key[1],
                          "model": key[2], "title": r.get("Post title", ""),
                          "raw": r, "ann": ann, "source": os.path.basename(path)})
    return items, dups, problems


def get_label(item, annotator, fid):
    _, step, fld, _, _, _ = FIELD[fid]
    v = item["ann"].get(annotator, {}).get(step, {}).get(fld)
    return None if v is None else str(v).strip()


def majority_vote(item, fid):
    vals = [get_label(item, a, fid) for a in ANNOTATORS]
    vals = [v for v in vals if v is not None]
    c = Counter(vals).most_common()
    if c and c[0][1] >= 2:
        return c[0][0], False
    return None, True  # tie -> adjudication


def load_meta(path):
    if not path:
        return {}, []
    meta = {}
    with open(path, newline="", encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        cols = rd.fieldnames or []
        for row in rd:
            key = tuple(str(row.get(k, "")).strip() for k in KEY)
            meta[key] = row
    return meta, cols


CTYPE_CODE = {"persuasive": "P", "hard_negative": "H", "easy_negative": "E"}


def load_patom_metrics(paths, condition):
    """Per-sample trajectory metrics from the PaTom repo (results/*metrics_per_sample.jsonl).

    PRISM = L * (-rho) * SC * sqrt(CG * CC)   (evaluation/eval/metrics.py in the repo)
    Rows lacking a "model" field (qwen_metrics_per_sample.jsonl) take it from the file name.
    """
    meta = {}
    for path in paths or []:
        default_model = "qwen" if "qwen" in os.path.basename(path).lower() else None
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if r.get("condition") != condition:
                    continue
                model = r.get("model") or default_model
                key = (str(r["post_id"]), str(r["comment_id"]), model)
                meta[key] = {
                    "comment_type": CTYPE_CODE.get(r.get("comment_type"), r.get("comment_type")),
                    "L": r.get("arc_length"), "SC": r.get("step_coherence"), "PRISM": r.get("PRISM"),
                    "rho": r.get("step_disp_cosine"), "CG": r.get("conclusion_grounding"),
                    "CC": r.get("chain_consistency"), "patom_score": r.get("score"),
                    "correctness": r.get("correctness"),
                }
    return meta


def meta_value(item, col):
    v = item.get("meta", {}).get(col)
    if isinstance(v, float) and math.isnan(v):
        return None
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(v)
    except ValueError:
        return str(v).strip()


# ---- Phase 1.3: failure-mode coding of annotator notes ---------------------

FAILURE_MODES = OrderedDict([
    ("F1", "OP-as-arbiter mismatch (Step 3$\\to$5 inconsistency)"),
    ("F2", "Latitude collapse on reframe (false assimilation)"),
    ("F3", "Step 4 tone / social misjudgment"),
    ("E1", "Latitude hedging (no committed classification)"),
    ("E2", "Hedge propagated into verdict"),
    ("E3", "Flawed Step 3 propagated into verdict"),
    ("E4", "Latitude misclassification (other)"),
    ("E5", "Unsupported / over-extended attribution"),
    ("E6", "Incomplete capture of argument"),
    ("OT", "Other / commentary on comment quality"),
])

RX = {
    "hedge": re.compile(r"hedg|can't decide|refusing to pick|equivocal|both ways|supports both|"
                        r"without clearly|overlapping outcomes|instead of committing|"
                        r"without settling|doesn't make an explicit|multiple classif", re.I),
    "hedge5": re.compile(r"hedg|indecision|unresolved|same issue as step 3|doesn't resolve", re.I),
    "mismatch5": re.compile(r"don't match|strays away|quietly change|doesn't match", re.I),
    "propag5": re.compile(r"inherit|flawed step 3|leans on step 3|step 3's wrong", re.I),
    "unsupported": re.compile(r"assumption|not (clearly )?grounded|not mentioned|does not clearly state|"
                              r"over-expand|too much as", re.I),
    "incomplete": re.compile(r"isn't just|underplays|misses|omits", re.I),
    "sources": re.compile(r"sources|studies|research", re.I),
}


def code_failure(step, note, fields):
    """Rule-based coding of one annotator note into the failure taxonomy."""
    if step == "Step 3":
        if RX["hedge"].search(note):
            return "E1"
        if fields.get("is_classification_correct") in ("No", "Partially"):
            if fields.get("classification_used") == "Assimilation":
                return "F2"
            return "E4"
        return "OT"
    if step == "Step 5":
        if RX["mismatch5"].search(note):
            return "F1"
        if RX["hedge5"].search(note):
            return "E2"
        if RX["propag5"].search(note):
            return "E3"
        if RX["unsupported"].search(note):
            return "E5"
        return "OT"
    if step == "Step 4":
        if RX["sources"].search(note):
            return "OT"
        return "F3"
    if step in ("Step 1", "Step 2"):
        if RX["unsupported"].search(note):
            return "E5"
        if RX["incomplete"].search(note):
            return "E6"
        return "OT"
    return "OT"


def extract_notes(items):
    notes = []
    for it in items:
        for a in ANNOTATORS:
            for step, fields in sorted(it["ann"].get(a, {}).items()):
                txt = str(fields.get("reasoning", "")).strip()
                if txt and txt.upper() != "N/A":
                    notes.append({"item": it, "annotator": a, "step": step, "text": txt,
                                  "fields": fields, "code": code_failure(step, txt, fields)})
    return notes


# =============================================================================
# LaTeX helpers
# =============================================================================

UNI = {"\u2014": "---", "\u2013": "--", "\u2018": "`", "\u2019": "'", "\u201c": "``",
       "\u201d": "''", "\u2026": "...", "\u00a0": " ", "\u2192": "$\\to$"}


def tex(s):
    s = str(s)
    out = []
    for ch in s:
        if ch in UNI:
            out.append(UNI[ch])
        elif ch == "\\":
            out.append("\\textbackslash{}")
        elif ch in "&%$#_{}":
            out.append("\\" + ch)
        elif ch == "~":
            out.append("\\textasciitilde{}")
        elif ch == "^":
            out.append("\\textasciicircum{}")
        elif ch in "<>":
            out.append("\\textless{}" if ch == "<" else "\\textgreater{}")
        elif ord(ch) > 127 and not ch.isalpha():
            out.append("?")
        else:
            out.append(ch)
    return "".join(out)


def f2(x, nd=2, signed=False):
    if x is None or isnan(x):
        return "---"
    s = f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}"
    return s.replace("-", "$-$") if not signed else s.replace("-", "$-$").replace("+", "$+$")


def pct(k, n, nd=1):
    return "---" if n == 0 else f"{100.0 * k / n:.{nd}f}\\%"


def fp(p):
    if p is None or isnan(p):
        return "---"
    return "$<$0.001" if p < 0.001 else f"{p:.3f}"


def na_box(text):
    return ("\\begin{mdframed}[backgroundcolor=warnbg,linewidth=0pt,innerleftmargin=6pt,"
            "innerrightmargin=6pt]\n\\small\\textbf{Not computable from current data.} "
            + text + "\n\\end{mdframed}\n")


def table(caption, label, colspec, header, rows, note=None, size="\\small", rowcolor=True):
    L = ["\\begin{table}[H]", "\\centering", size, f"\\begin{{tabular}}{{{colspec}}}",
         "\\toprule", " & ".join(header) + " \\\\", "\\midrule"]
    for i, r in enumerate(rows):
        if r == "MIDRULE":
            L.append("\\midrule")
            continue
        pre = "\\rowcolor{rowgray} " if rowcolor and i % 2 == 0 else ""
        L.append(pre + " & ".join(str(c) for c in r) + " \\\\")
    L.append("\\bottomrule")
    if note:
        L.append(f"\\multicolumn{{{len(header)}}}{{p{{0.95\\linewidth}}}}{{\\footnotesize {note}}} \\\\")
    L += ["\\end{tabular}", f"\\caption{{{caption}}}", f"\\label{{{label}}}", "\\end{table}", ""]
    return "\n".join(L)


# =============================================================================
# Analysis
# =============================================================================

def run(args):
    rng = random.Random(SEED)
    items, dups, problems = load_items(args.data)
    meta = load_patom_metrics(args.patom_metrics, args.condition)
    csv_meta, meta_cols = load_meta(args.meta)
    for k, row in csv_meta.items():  # CSV values override / extend repo metrics
        meta.setdefault(k, {}).update({c: v for c, v in row.items() if c not in KEY})
    matched = 0
    for it in items:
        it["meta"] = meta.get(it["key"], {})
        matched += bool(it["meta"])
    avail = {c: any(meta_value(it, c) is not None for it in items) for c in MISSING_PLAN_FIELDS}

    models = sorted({it["model"] for it in items}, key=lambda m: list(MODEL_NAMES).index(m)
                    if m in MODEL_NAMES else 99)
    mname = lambda m: MODEL_NAMES.get(m, m)
    N = len(items)

    # majority votes
    ties = Counter()
    for it in items:
        it["mv"] = {}
        for fid in FIELD:
            lab, tie = majority_vote(it, fid)
            it["mv"][fid] = lab
            if tie:
                ties[fid] += 1
                it.setdefault("ties", []).append(fid)
        # ordinal fallback (median of 3) for ordinal fields, used for correlations
        it["ord"] = {}
        for fid, f in FIELD.items():
            if f[4]:
                vals = sorted(ORDINAL_MAP[v] for v in
                              (get_label(it, a, fid) for a in ANNOTATORS) if v is not None)
                it["ord"][fid] = vals[len(vals) // 2] if vals else None
        it["mean"] = {fid: (sum(ORDINAL_MAP[get_label(it, a, fid)] for a in ANNOTATORS) / 3.0)
                      for fid, f in FIELD.items() if f[4]}
        # Step 3a derived error type
        c, cls = it["mv"]["s3_correct"], it["mv"]["s3_class"]
        if c is None or cls is None:
            it["s3_err"] = "tie"
        elif c == "Yes":
            it["s3_err"] = "correct"
        else:
            it["s3_err"] = {"Within latitude": "within_err", "Assimilation": "assim_err",
                            "Contrast": "contrast_err"}[cls]
        # chain-clean proxy for Step 6: every step's majority rating == 2
        it["chain_clean"] = all(it["mv"][f"s{k}_rating"] == "2" for k in range(1, 6))

    notes = extract_notes(items)
    for it in items:
        it["fmodes"] = sorted({n["code"] for n in notes if n["item"] is it})

    out = []
    w = out.append

    # ---------------------------------------------------------------- preamble
    w(PREAMBLE)
    w("\\begin{document}\n\\maketitle\n")
    w("\\begin{abstract}\n")
    w(f"This document reports the results of executing the \\pbench{{}} analysis plan "
      f"(Appendix~A, Phases~1--7) on the annotation export "
      f"\\texttt{{{tex(', '.join(os.path.basename(p) for p in args.data))}}} "
      f"($N={N}$ items, {len(ANNOTATORS)} annotators, "
      + ", ".join(f"{mname(m)} $n={sum(it['model'] == m for it in items)}$" for m in models) + "). "
      "All numbers are generated by \\texttt{patom\\_bench\\_analysis.py}; "
      "trajectory metrics (PRISM, $L$, SC), comment type and the \\patom{} score are taken from "
      "the PaTom repository's per-sample results. Analyses that depend on fields available in "
      "neither source (Step~3b, Step~6, $\\Delta_3$, agreed-wrong flags) are marked as not "
      "computable and will populate automatically when supplied via \\texttt{--meta}.\n")
    w("\\end{abstract}\n")

    # schema mapping box
    w("\\section*{Schema mapping}\n")
    w("The export records a 0/1/2 quality \\texttt{rating} per step plus four categorical "
      "fields. These are mapped onto the paper's schema (Table~\\ref{tab:schema-map}); "
      "ordinal codings follow \\paper{Human Labels vs.\\ Trajectory Metrics} section "
      "(correct\\,=\\,2, partial/underdetermined\\,=\\,1, error\\,=\\,0).\n")
    w(table("Mapping from export fields to the \\pbench{} schema.", "tab:schema-map",
            "p{3.3cm}p{5.6cm}p{5.2cm}",
            ["\\textbf{Paper dimension}", "\\textbf{Export field}", "\\textbf{Coding used here}"],
            [["Steps 1, 2, 4 quality", "\\texttt{Step k.rating}", "0 / 1 / 2 (ordinal)"],
             ["Step 3a label", "\\texttt{Step 3.classification\\_used}",
              "Within latitude / Assimilation / Contrast"],
             ["Step 3a accuracy", "\\texttt{Step 3.is\\_classification\\_correct}",
              "Yes\\,=\\,2 (correct\\_targeting), Partially\\,=\\,1 (underdetermined), No\\,=\\,0"],
             ["Step 3a error type", "classification\\_used $\\times$ accuracy",
              "classification used on items not judged fully correct"],
             ["Step 5 grounding", "\\texttt{Step 5.verdict\\_follows\\_directly}",
              "Yes\\,=\\,2 (chain\\_grounded), Partially\\,=\\,1, No\\,=\\,0"],
             ["Step 5 new reasoning", "\\texttt{Step 5.introduces\\_new\\_reasoning}", "Yes / No"],
             ["Step 3b profile grounding", "\\emph{absent}", "---"],
             ["Step 6 chain holistic", "\\emph{absent}",
              "proxy: all five step ratings $=2$ (majority)"],
             ["Comment type (P/H/E)", "PaTom repo \\texttt{comment\\_type}" if avail["comment_type"]
              else "\\emph{absent} (needs \\texttt{--meta})", "persuasive/hard/easy $\\to$ P/H/E"],
             ["$L$, SC, PRISM", "PaTom repo \\texttt{metrics\\_per\\_sample.jsonl}" if avail["PRISM"]
              else "\\emph{absent} (needs \\texttt{--meta})", "\\texttt{arc\\_length}, "
              "\\texttt{step\\_coherence}, \\texttt{PRISM}"],
             ["\\patom{} final score", "PaTom repo \\texttt{score}" if avail["patom_score"]
              else "\\emph{absent}", "chain-condition score"],
             ["$\\Delta_3$, agreed-wrong", "\\emph{absent} (not in repo)", "---"]]))

    # ================================================================ PHASE 1
    w("\\section{Phase 1 --- Data Preparation}\\label{sec:p1}\n")
    w("\\subsection{1.1 Merge and integrity checks}\n")
    w("\\begin{itemize}[leftmargin=*,itemsep=1pt]\n")
    w(f"\\item Input files: {len(args.data)} "
      f"({tex(', '.join(os.path.basename(p) for p in args.data))}); "
      f"{N} unique items after merge.\n")
    w(f"\\item Key \\texttt{{(post\\_id, comment\\_id, model)}}: {len(dups)} duplicate(s) flagged"
      + (": " + tex("; ".join(f"{k} in {a} & {b}" for k, a, b in dups)) if dups else "") + ".\n")
    w(f"\\item Schema problems (missing annotators/fields): {len(problems)}"
      + ("." if not problems else ": " + tex("; ".join(problems[:10])) + ".") + "\n")
    npost = len({it["post_id"] for it in items})
    npair = len({(it["post_id"], it["comment_id"]) for it in items})
    w(f"\\item {npost} unique posts, {npair} unique (post, comment) pairs; "
      f"{N - npair} item(s) are the same (post, comment) judged under a second model.\n")
    w("\\end{itemize}\n")

    w("\\subsection{1.2 Majority vote}\n")
    rows = []
    for fid, f in FIELD.items():
        rows.append([f[5], str(N - ties[fid]), str(ties[fid]),
                     tex(", ".join(it["post_id"] for it in items if fid in it.get("ties", []))) or "---"])
    w(table("Majority-vote resolution per field (3 annotators). Ties (three distinct labels) "
            "are flagged for Pass-2 adjudication.", "tab:mv",
            "p{5.4cm}ccp{5.0cm}",
            ["\\textbf{Field}", "\\textbf{Resolved}", "\\textbf{Ties}", "\\textbf{Tied items (post\\_id)}"],
            rows))

    w("\\subsection{1.3 Failure-mode coding of annotator notes}\n")
    w(f"Annotators wrote {len(notes)} free-text notes (all others are \\texttt{{N/A}}). "
      "Each note was coded with a deterministic keyword/field rule set "
      "(\\texttt{code\\_failure()} in the script) into the paper's three failure modes "
      "(F1--F3, \\paper{Failure Mode Taxonomy}) plus emergent categories (E1--E6). "
      "The full coded list is in Appendix~\\ref{app:notes} for audit.\n")

    w("\\subsection{1.4 Trajectory-metric match}\n")
    if args.meta or args.patom_metrics:
        srcs = [os.path.basename(p) for p in (args.patom_metrics or [])] + (
            [os.path.basename(args.meta)] if args.meta else [])
        w(f"Sources: \\texttt{{{tex(', '.join(srcs))}}} (per-sample metrics from the PaTom repository, "
          f"\\url{{https://github.com/baktash81/PaTom}}, condition \\texttt{{{tex(args.condition)}}} "
          f"$=$ \\patom{{}} chain). {matched}/{N} items matched on "
          f"\\texttt{{(post\\_id, comment\\_id, model)}}. Plan fields available: "
          f"{tex(', '.join(c for c in MISSING_PLAN_FIELDS if avail[c])) or 'none'}; "
          f"missing: {tex(', '.join(c for c in MISSING_PLAN_FIELDS if not avail[c])) or 'none'}.\n\n"
          "PRISM is defined in the repository (\\texttt{evaluation/eval/metrics.py}) over sentence "
          "embeddings of the chain steps as\n"
          "\\[\\text{PRISM} = L\\cdot(-\\rho)\\cdot \\mathrm{SC}\\cdot\\sqrt{\\mathrm{CG}\\cdot\\mathrm{CC}},\\]\n"
          "with $L$ the arc length, $\\rho$ the mean cosine between consecutive displacement vectors, "
          "SC the ROSCOE step coherence, CG the ReCEval conclusion grounding and CC the chain "
          "consistency. The repository does not define or compute $\\Delta_3$ (step-3 deflection), "
          "so Step~3a $\\times$ $\\Delta_3$ remains open.\n")
        ctypes = Counter(meta_value(it, "comment_type") for it in items)
        if avail["comment_type"] and len([c for c in ctypes if c]) == 1:
            w(na_box(f"All {N} matched pilot items have comment type "
                     f"\\texttt{{{tex(next(c for c in ctypes if c))}}}, so every P/H/E comparison in the "
                     "plan is untestable on this pilot and is reported descriptively only."))
    else:
        w(na_box("No trajectory-metric file was supplied (\\texttt{--meta}). The export contains no "
                 "$L$, $\\Delta_3$, SC, or PRISM values, so items could not be matched to "
                 "\\citet{CITATION_PATOM} metrics."))

    w("\\subsection{1.5 Final counts}\n")
    types = ["P", "H", "E"]
    rows = []
    for m in models:
        mi = [it for it in items if it["model"] == m]
        if avail["comment_type"]:
            rows.append([mname(m)] + [str(sum(meta_value(it, "comment_type") == t for it in mi))
                                      for t in types] + [str(len(mi))])
        else:
            rows.append([mname(m), "---", "---", "---", str(len(mi))])
    rows.append("MIDRULE")
    rows.append(["\\textbf{Total}"] + ([str(sum(meta_value(it, "comment_type") == t for it in items))
                                        for t in types] if avail["comment_type"] else ["---"] * 3)
                + [f"\\textbf{{{N}}}"])
    w(table("Dataset composition by model and comment type (updates \\paper{Dataset Statistics} table). "
            "``---'' = comment type not in export.", "tab:stats-new",
            "lcccc", ["\\textbf{Model}", "\\textbf{P}", "\\textbf{H}", "\\textbf{E}", "\\textbf{Total}"],
            rows))
    w(f"Step-level labels in this release: {N} items $\\times$ {len(FIELDS)} annotated fields "
      f"$\\times$ 3 annotators $=$ {N * len(FIELDS) * 3} labels.\n")

    # ================================================================ PHASE 2
    w("\\section{Phase 2 --- Inter-Annotator Agreement}\\label{sec:p2}\n")
    w("For every field we compute Cohen's $\\kappa$ for the three annotator pairs and their mean "
      "$\\bar\\kappa$, Krippendorff's $\\alpha$ (nominal; ordinal in addition for ordinal fields) "
      "with a 95\\% item-bootstrap CI, three-way exact agreement, and Gwet's AC1. "
      "AC1 is included because most fields are heavily skewed toward a single label, where "
      "$\\kappa$/$\\alpha$ are known to be deflated despite near-perfect raw agreement "
      "(the ``kappa paradox'').\n")

    iaa = {}
    for fid, f in FIELD.items():
        labels = f[3]
        units = [[get_label(it, a, fid) for a in ANNOTATORS if get_label(it, a, fid) is not None]
                 for it in items]
        pairs = {}
        for a, b in itertools.combinations(ANNOTATORS, 2):
            xa = [get_label(it, a, fid) for it in items]
            xb = [get_label(it, b, fid) for it in items]
            keep = [(p, q) for p, q in zip(xa, xb) if p is not None and q is not None]
            pairs[(a, b)] = cohen_kappa([p for p, _ in keep], [q for _, q in keep], labels)
        valid = [v for v in pairs.values() if not isnan(v)]
        kbar = sum(valid) / len(valid) if valid else nan()
        a_nom = krippendorff_alpha(units, labels, "nominal")
        a_ord = krippendorff_alpha(units, labels, "ordinal") if f[4] else nan()
        ci = bootstrap_ci(units, lambda u: krippendorff_alpha(u, labels, "nominal"), rng)
        dist = Counter(v for u in units for v in u)
        iaa[fid] = {"pairs": pairs, "kbar": kbar, "a_nom": a_nom, "a_ord": a_ord, "ci": ci,
                    "exact": exact3(units), "ac1": gwet_ac1(units, labels),
                    "top": max(dist.values()) / sum(dist.values())}

    rows = []
    for fid, f in FIELD.items():
        r = iaa[fid]
        flag = "$\\dagger$" if (not isnan(r["kbar"]) and r["kbar"] < 0.40) else ""
        rows.append([f[5] + flag] + [f2(r["pairs"][p]) for p in itertools.combinations(ANNOTATORS, 2)]
                    + [f2(r["kbar"]), f2(r["a_nom"]), f2(r["a_ord"]),
                       f"[{f2(r['ci'][0])}, {f2(r['ci'][1])}]",
                       pct(r["exact"] * 100, 100), f2(r["ac1"]), pct(r["top"] * 100, 100, 0)])
    rows.append(["Step 3b --- Profile grounding"] + ["---"] * 10)
    rows.append(["Step 6 --- Chain holistic"] + ["---"] * 10)
    w("\\begin{table*}[t]\n\\centering\\footnotesize\\setlength{\\tabcolsep}{3.5pt}\n"
      "\\begin{tabular}{p{3.6cm}cccccccccc}\n\\toprule\n"
      "\\textbf{Field} & $\\kappa_{12}$ & $\\kappa_{13}$ & $\\kappa_{23}$ & $\\bar\\kappa$ & "
      "$\\alpha_{\\text{nom}}$ & $\\alpha_{\\text{ord}}$ & $\\alpha$ 95\\% CI & 3-way & AC1 & Modal \\\\\n\\midrule\n")
    for i, r in enumerate(rows):
        w(("\\rowcolor{rowgray} " if i % 2 == 0 else "") + " & ".join(r) + " \\\\\n")
    w("\\bottomrule\n\\end{tabular}\n"
      "\\caption{Inter-annotator agreement per field (updates \\paper{IAA} table). "
      "$\\kappa_{ij}$: Cohen's $\\kappa$ for annotators A$i$/A$j$; $\\alpha$: Krippendorff's $\\alpha$ "
      "(3 annotators); 3-way: exact three-annotator agreement; AC1: Gwet's AC1; Modal: share of all "
      "labels that fall in the most frequent category. $\\dagger$: $\\bar\\kappa<0.40$, flagged for "
      "schema revision (Phase 2.6). ``---'' for $\\kappa$ = undefined (a rater used one category only).}\n"
      "\\label{tab:iaa-new}\n\\end{table*}\n\n")

    # 2.4 per-label kappa within Step 3a
    w("\\subsection{2.4 Per-label agreement within Step 3a}\n")
    rows = []
    for fid in ("s3_class", "s3_correct"):
        for lab in FIELD[fid][3]:
            ks = []
            for a, b in itertools.combinations(ANNOTATORS, 2):
                xa = [get_label(it, a, fid) == lab for it in items]
                xb = [get_label(it, b, fid) == lab for it in items]
                ks.append(cohen_kappa(xa, xb, [True, False]))
            units = [[get_label(it, a, fid) == lab for a in ANNOTATORS] for it in items]
            nlab = sum(u.count(True) for u in units)
            valid = [k for k in ks if not isnan(k)]
            rows.append([FIELD[fid][2].replace("_", "\\_"), tex(lab), str(nlab)]
                        + [f2(k) for k in ks]
                        + [f2(sum(valid) / len(valid) if valid else nan()),
                           f2(krippendorff_alpha(units, [False, True]))])
    w(table("One-vs-rest agreement for each Step~3a label. $n$ = number of times the label was "
            "assigned across the 3 annotators.", "tab:perlabel",
            "llccccccc", ["\\textbf{Field}", "\\textbf{Label}", "$n$", "$\\kappa_{12}$", "$\\kappa_{13}$",
                          "$\\kappa_{23}$", "$\\bar\\kappa$", "$\\alpha$"], rows))
    lab_k = {}
    for r in rows[:3]:
        lab_k[r[1]] = r[-2]
    w(f"\\textbf{{Assimilation vs.\\ contrast.}} For \\texttt{{classification\\_used}}, "
      f"$\\bar\\kappa$ is {lab_k.get('Assimilation')} for Assimilation versus "
      f"{lab_k.get('Contrast')} for Contrast and {lab_k.get('Within latitude')} for Within latitude.\n\n")

    w("\\subsection{2.5 Step 3b profile grounding}\n")
    w(na_box("The export has no Step~3b (profile-grounded / text-only / mixed) field."))

    w("\\subsection{2.6 Steps flagged for schema revision ($\\bar\\kappa<0.40$)}\n")
    flagged = [fid for fid in FIELD if not isnan(iaa[fid]["kbar"]) and iaa[fid]["kbar"] < 0.40]
    if flagged:
        w("\\begin{itemize}[leftmargin=*,itemsep=1pt]\n")
        for fid in flagged:
            r = iaa[fid]
            paradox = r["top"] >= 0.80 and r["exact"] >= 0.70
            w(f"\\item {FIELD[fid][5]}: $\\bar\\kappa={r['kbar']:.2f}$, 3-way {pct(r['exact']*100,100)}, "
              f"AC1\\,=\\,{f2(r['ac1'])}. "
              + ("Low $\\kappa$ co-occurs with high raw agreement and a modal-category share of "
                 f"{pct(r['top']*100,100,0)}: this is chiefly a prevalence effect rather than genuine "
                 "disagreement; revisit after the full dataset adds label variety."
                 if paradox else "Agreement is low on both chance-corrected and raw measures; "
                 "candidate for guideline revision.") + "\n")
        w("\\end{itemize}\n")
    else:
        w("No field falls below $\\bar\\kappa=0.40$.\n")

    # ================================================================ PHASE 3
    w("\\section{Phase 3 --- Label Distributions}\\label{sec:p3}\n")
    w("\\subsection{3.1 Majority-vote label frequencies by model}\n")
    rows = []
    for fid, f in FIELD.items():
        for lab in f[3] + ["tie"]:
            cnt = []
            tot = 0
            for m in models + ["ALL"]:
                mi = [it for it in items if m == "ALL" or it["model"] == m]
                k = sum((it["mv"][fid] or "tie") == lab for it in mi)
                cnt.append(f"{k} ({pct(k, len(mi), 0)})")
                tot += k
            if lab == "tie" and all(c.startswith("0 ") for c in cnt):
                continue
            rows.append([f[5] if lab == f[3][0] else "", tex(lab)] + cnt)
    w(table("Majority-vote label frequencies per field, by model (count and \\% of items).",
            "tab:dist", "p{5.0cm}l" + "c" * (len(models) + 1),
            ["\\textbf{Field}", "\\textbf{Label}"] + [f"\\textbf{{{mname(m)}}}" for m in models]
            + ["\\textbf{All}"], rows, size="\\footnotesize", rowcolor=False))
    if not avail["comment_type"]:
        w(na_box("Breakdown by comment type (P/H/E) requires \\texttt{comment\\_type} in \\texttt{--meta}."))
    else:
        rows = []
        for t in types:
            ti = [it for it in items if meta_value(it, "comment_type") == t]
            rows.append([t, str(len(ti))] + [pct(sum(it["s3_err"] == e for it in ti), len(ti))
                                               for e in ("correct", "within_err", "assim_err", "contrast_err")]
                        + [pct(sum(it["mv"]["s5_follows"] == "Yes" for it in ti), len(ti)),
                           pct(sum(it["chain_clean"] for it in ti), len(ti))])
        w(table("Key labels by comment type.", "tab:dist-type", "lccccccc",
                ["\\textbf{Type}", "$n$", "3a correct", "within err", "assim.\\ err", "contrast err",
                 "S5 follows", "chain-clean"], rows))

    # per-annotator Step 3a view (paper reports per-annotator)
    w("\\paragraph{Per-annotator Step 3a view.}\n")
    rows = []
    for a in ANNOTATORS:
        cls = Counter(get_label(it, a, "s3_class") for it in items)
        cor = Counter(get_label(it, a, "s3_correct") for it in items)
        rows.append([a] + [pct(cls[l], N) for l in FIELD["s3_class"][3]]
                    + [pct(cor[l], N) for l in ("Yes", "Partially", "No")])
    w(table("Step~3a labels per annotator (\\% of items).", "tab:per-ann",
            "lcccccc", ["\\textbf{Ann.}", "Within", "Assim.", "Contrast", "Correct: Yes",
                        "Partially", "No"], rows))

    # 3.2 Step 3a x comment type (or model)
    w("\\subsection{3.2 Step 3a error type $\\times$ comment type}\n")
    err_labels = {"correct": "correct", "within_err": "within-latitude err.",
                  "assim_err": "assimilation err.", "contrast_err": "contrast err.", "tie": "tie"}

    def err_table(group_fn, groups, gname, caption, label):
        rows = []
        for g in groups:
            gi = [it for it in items if group_fn(it) == g]
            rows.append([tex(gname(g)), str(len(gi))]
                        + [f"{sum(it['s3_err']==e for it in gi)} ({pct(sum(it['s3_err']==e for it in gi), len(gi), 0)})"
                           for e in ("correct", "within_err", "assim_err", "contrast_err")])
        sub = [it for it in items if it["s3_err"] != "tie" and group_fn(it) in groups]
        res = chi2_test([group_fn(it) for it in sub], [it["s3_err"] for it in sub], rng)
        bin_res = chi2_test([group_fn(it) for it in sub],
                            [it["s3_err"] == "correct" for it in sub], rng)
        w(table(caption, label, "lccccc",
                ["\\textbf{Group}", "$n$", "Correct", "Within err.", "Assim.\\ err.", "Contrast err."], rows))
        return res, bin_res

    def chi_sentence(res, what):
        if res is None:
            return f"{what}: not testable (a margin has a single category).\n"
        return (f"{what}: $\\chi^2({res['df']})={res['chi2']:.2f}$, asymptotic $p={fp(res['p_asym'])}$, "
                f"Monte-Carlo permutation $p={fp(res['p_perm'])}$ ({N_PERM:,} permutations), "
                f"Cram\\'er's $V={res['V']:.2f}$, $n={res['n']}$.\n")

    if avail["comment_type"]:
        res, bres = err_table(lambda it: meta_value(it, "comment_type"), types, lambda g: g,
                              "Step~3a error type by comment type.", "tab:3a-type")
        w(chi_sentence(res, "Error type $\\times$ comment type") + "\n\n")
        w(chi_sentence(bres, "Any error vs.\\ correct $\\times$ comment type") + "\n\n")
    else:
        w(na_box("The planned test (Step~3a $\\times$ comment type; hypothesis: H $>$ P in "
                 "contrast/assimilation error) needs \\texttt{comment\\_type}. As the closest available "
                 "stratifier, the same test is run by \\emph{model} below."))
    res, bres = err_table(lambda it: it["model"], models, mname,
                          "Step~3a error type (majority vote) by model. An error is a classification "
                          "not judged fully correct (\\texttt{is\\_classification\\_correct} $\\neq$ Yes), "
                          "typed by the classification the model used.", "tab:3a-model")
    w(chi_sentence(res, "Error type $\\times$ model") + "\n\n")
    w(chi_sentence(bres, "Any error vs.\\ correct $\\times$ model") + "\n\n")
    if len(models) == 2:
        a_, b_ = [[sum(it["s3_err"] == "correct" for it in items if it["model"] == m),
                   sum(it["s3_err"] not in ("correct", "tie") for it in items if it["model"] == m)]
                  for m in models]
        w(f"Fisher exact test (correct vs.\\ error, {mname(models[0])} vs.\\ {mname(models[1])}): "
          f"$p={fp(fisher_exact_2x2(a_[0], a_[1], b_[0], b_[1]))}$.\n\n")
    w("With $n=" + str(N) + "$ and sparse error cells these tests have very low power; they are "
      "reported for completeness and should be re-run on the merged dataset.\n")

    # 3.3 Step 5 verdict follows by model
    w("\\subsection{3.3 Step 5 \\texttt{verdict\\_follows\\_directly} by model (H: $>90\\%$ all models)}\n")
    rows = []
    for m in models + ["ALL"]:
        mi = [it for it in items if m == "ALL" or it["model"] == m]
        k = sum(it["mv"]["s5_follows"] == "Yes" for it in mi)
        n = len(mi)
        lo, hi = wilson(k, n)
        p = binom_sf(k, n, 0.90)
        kn = sum(it["mv"]["s5_newreason"] == "Yes" for it in mi)
        rows.append([mname(m) if m != "ALL" else "\\textbf{All}", str(n), f"{k}/{n}", pct(k, n),
                     f"[{100*lo:.1f}, {100*hi:.1f}]", fp(p),
                     "yes" if k / n > 0.90 else "no", pct(kn, n)])
    w(table("Step~5 verdict follows directly (majority \\texttt{Yes}) by model, with Wilson 95\\% CI "
            "and one-sided exact binomial test of $H_0\\!: \\pi\\le0.90$ vs.\\ $H_1\\!: \\pi>0.90$. "
            "Last column: majority \\texttt{introduces\\_new\\_reasoning}\\,=\\,Yes.",
            "tab:s5", "lccccccc", ["\\textbf{Model}", "$n$", "Yes", "\\%", "95\\% CI",
                                    "$p$ ($>$90\\%)", "Point $>$90\\%?", "New reasoning"], rows))
    w("A point estimate above 90\\% supports the hypothesis descriptively; with $n\\le 50$ the "
      "Wilson intervals are wide and the binomial test cannot establish $\\pi>0.90$ unless nearly "
      "every item follows.\n")

    # 3.4 chain holistic
    w("\\subsection{3.4 Chain holistic (Step 6) by model and comment type}\n")
    w(na_box("Step~6 (yes / marginal / no) is not in the export, and comment type is unavailable, "
             "so the hypothesis (H $>$ E in `yes' rate) cannot be tested. As a transparent proxy we "
             "report the share of items whose \\emph{majority} rating is 2 on all five steps "
             "(``chain-clean'')."))
    rows = []
    for m in models + ["ALL"]:
        mi = [it for it in items if m == "ALL" or it["model"] == m]
        k = sum(it["chain_clean"] for it in mi)
        lo, hi = wilson(k, len(mi))
        rows.append([mname(m) if m != "ALL" else "\\textbf{All}", str(len(mi)), f"{k}", pct(k, len(mi)),
                     f"[{100*lo:.1f}, {100*hi:.1f}]"])
    w(table("Chain-clean proxy for Step~6 by model.", "tab:s6proxy", "lcccc",
            ["\\textbf{Model}", "$n$", "Chain-clean", "\\%", "95\\% CI"], rows))
    if len(models) == 2:
        c = [[sum(it["chain_clean"] for it in items if it["model"] == m),
              sum(not it["chain_clean"] for it in items if it["model"] == m)] for m in models]
        w(f"Fisher exact test across models: $p={fp(fisher_exact_2x2(c[0][0], c[0][1], c[1][0], c[1][1]))}$.\n")

    # ================================================================ PHASE 4
    w("\\section{Phase 4 --- Cross-Model Comparison (shared items)}\\label{sec:p4}\n")
    by_pair = defaultdict(dict)
    for it in items:
        by_pair[(it["post_id"], it["comment_id"])][it["model"]] = it
    shared = {k: v for k, v in by_pair.items() if len(v) >= 2}
    w(f"The plan targets 150 items shared across all three model conditions. The current export "
      f"contains \\textbf{{{len(shared)}}} (post, comment) pair(s) judged by more than one model "
      f"({', '.join(sorted({'/'.join(mname(m) for m in sorted(v, key=models.index)) for v in shared.values()}))}"
      f"); no Qwen items are present. Results below are therefore descriptive only.\n\n")

    w("\\subsection{4.1 Per-step label agreement across model conditions}\n")
    rows = []
    for fid, f in FIELD.items():
        agree = tot = 0
        for v in shared.values():
            labs = [v[m]["mv"][fid] for m in v]
            if None in labs:
                continue
            tot += 1
            agree += len(set(labs)) == 1
        rows.append([f[5], f"{agree}/{tot}", pct(agree, tot, 0)])
    agree = sum(len({v[m]["s3_err"] for m in v}) == 1 for v in shared.values())
    rows.append(["Step 3a --- derived error type", f"{agree}/{len(shared)}", pct(agree, len(shared), 0)])
    w(table("Agreement of majority-vote labels between model conditions on shared items.",
            "tab:xmodel", "p{6cm}cc", ["\\textbf{Field}", "\\textbf{Agree}", "\\%"], rows))

    w("\\subsection{4.2 Step 3a divergence (qualitative)}\n")
    div = [(k, v) for k, v in shared.items()
           if len({v[m]["mv"]["s3_class"] for m in v}) > 1 or len({v[m]["s3_err"] for m in v}) > 1]
    w(f"{len(div)} of {len(shared)} shared pairs diverge on Step~3a (classification used or "
      "correctness). Each is listed with the majority labels per model and any annotator notes "
      "on Steps~3/5 (the plan calls for 10--15 such items; more will be available after merging).\n\n")
    if div:
        w("\\begin{longtable}{p{2.6cm}p{2.0cm}p{2.4cm}p{1.4cm}p{6.3cm}}\n\\toprule\n"
          "\\textbf{Post} & \\textbf{Model} & \\textbf{3a class.} & \\textbf{Correct} & "
          "\\textbf{Annotator notes (Step 3/5)} \\\\\n\\midrule\\endhead\n")
        for (pid, cid), v in div:
            first = True
            for m in sorted(v, key=models.index):
                it = v[m]
                ns = [f"{n['annotator']}/{n['step'][-1]}: {n['text']}" for n in notes
                      if n["item"] is it and n["step"] in ("Step 3", "Step 5")]
                w((f"\\textit{{{tex(it['title'][:80])}}} ({tex(pid)})" if first else "") + " & "
                  + mname(m) + " & " + tex(it["mv"]["s3_class"] or "tie") + " & "
                  + tex(it["mv"]["s3_correct"] or "tie") + " & "
                  + ("\\scriptsize " + tex(" | ".join(ns)) if ns else "---") + " \\\\\n")
                first = False
            w("\\midrule\n")
        w("\\bottomrule\n\\caption{Shared items with cross-model Step~3a divergence.}\\label{tab:div} \\\\\n"
          "\\end{longtable}\n")

    w("\\subsection{4.3 Step 4 social management: Claude vs.\\ GPT-5}\n")
    w("The export has only the Step~4 quality rating (not the complete/partial/conflated/absent "
      "label set), so the comparison uses the rating distribution.\n\n")
    rows = []
    for scope, pool in (("All items", items),
                        ("Shared items", [it for v in shared.values() for it in v.values()])):
        for m in models:
            mi = [it for it in pool if it["model"] == m]
            c = Counter(it["mv"]["s4_rating"] or "tie" for it in mi)
            rows.append([scope if m == models[0] else "", mname(m), str(len(mi))]
                        + [f"{c[l]} ({pct(c[l], len(mi), 0)})" for l in ("2", "1", "0")])
    w(table("Step~4 majority rating by model.", "tab:s4", "llccccc",
            ["\\textbf{Scope}", "\\textbf{Model}", "$n$", "2", "1", "0"], rows))
    if len(models) == 2:
        c = [[sum(it["mv"]["s4_rating"] == "2" for it in items if it["model"] == m),
              sum(it["mv"]["s4_rating"] != "2" for it in items if it["model"] == m)] for m in models]
        w(f"Fisher exact test (rating 2 vs.\\ $<$2, all items): "
          f"$p={fp(fisher_exact_2x2(c[0][0], c[0][1], c[1][0], c[1][1]))}$. "
          "Annotator-level: " + ", ".join(
              f"{mname(m)} {pct(sum(get_label(it,a,'s4_rating')=='2' for it in items if it['model']==m for a in ANNOTATORS), 3*sum(it['model']==m for it in items))}"
              for m in models) + " of individual Step~4 ratings are 2.\n")

    # ================================================================ PHASE 5
    w("\\section{Phase 5 --- Human Labels vs.\\ Trajectory Metrics}\\label{sec:p5}\n")
    plan5 = [("Step 3a (ordinal)", "s3_correct", "delta3", "$\\Delta_3$"),
             ("Step 3a (ordinal)", "s3_correct", "L", "$L$"),
             ("Step 5 grounding (ordinal)", "s5_follows", "PRISM", "PRISM"),
             ("Step 5 grounding (ordinal)", "s5_follows", "SC", "SC"),
             ("Chain holistic", "chain", "L", "$L$")]
    def human(fid, how):
        if fid == "chain":  # Step 6 proxy
            if how == "mv":
                return [float(it["chain_clean"]) for it in items]
            return [sum(it["mean"][f"s{k}_rating"] for k in range(1, 6)) for it in items]
        return [it["ord" if how == "mv" else "mean"][fid] for it in items]

    def rho_cells(xs, col):
        res = spearman(xs, [meta_value(it, col) for it in items], rng)
        if not res:
            return ["---", "---"], "---"
        if isnan(res["rho"]):
            return ["n/d", "---"], str(res["n"])
        return [f2(res["rho"]), fp(res["p"])], str(res["n"])

    rows = []
    for name, fid, col, disp in plan5:
        if not avail.get(col):
            rows.append([name, disp] + ["---"] * 5)
            continue
        mv, n = rho_cells(human(fid, "mv"), col)
        mn, _ = rho_cells(human(fid, "mean"), col)
        rows.append([name + (" (proxy)" if fid == "chain" else ""), disp] + mv + mn + [n])
    w(table("Spearman correlations between human labels and trajectory metrics "
            "(updates \\paper{correlation} table). MV: majority vote (median of 3 for ordinal "
            "fields), as in the plan; Mean: mean of the three annotators' ordinal codes. "
            "$p$: two-sided permutation test. n/d: undefined because the human label is constant "
            "across items. ``---'': metric not available. Chain holistic uses the chain-clean proxy "
            "(MV) or the summed mean step ratings (Mean).", "tab:corr-new",
            "p{3.6cm}lccccc", ["\\textbf{Human label}", "\\textbf{Metric}", "$\\rho_{\\text{MV}}$",
                               "$p_{\\text{MV}}$", "$\\rho_{\\text{Mean}}$", "$p_{\\text{Mean}}$", "$n$"],
            rows))
    if avail["PRISM"]:
        w("Hypotheses from the paper: Step~3a $\\times$ $\\Delta_3$ with $\\rho>0.30$ (not testable, "
          "$\\Delta_3$ unavailable) and Step~5 grounding $\\times$ PRISM with $\\rho>0.25$, $p<0.05$. "
          "Because the majority Step~5 grounding label is \\texttt{Yes} for every item, the "
          "planned majority-vote test is undefined; the annotator-mean column is the usable estimate.\n\n")
        comps = [("L", "$L$"), ("rho", "$\\rho$ (disp.\\ cosine)"), ("SC", "SC"), ("CG", "CG"),
                 ("CC", "CC"), ("PRISM", "PRISM"), ("patom_score", "\\patom{} score")]
        comps = [c for c in comps if avail.get(c[0]) or any(meta_value(it, c[0]) is not None for it in items)]
        hl = [("s3_correct", "3a"), ("s3_rating", "S3 rt."), ("s5_follows", "S5 grd."),
              ("s5_rating", "S5 rt."), ("chain", "Chain")]
        rows = []
        for col, disp in comps:
            vals = [meta_value(it, col) for it in items]
            v = [x for x in vals if x is not None]
            cells = []
            for fid, _ in hl:
                res = spearman(human(fid, "mean"), vals, rng)
                cells.append("---" if not res or isnan(res["rho"]) else
                             f2(res["rho"]) + ("$^{*}$" if res["p"] < 0.05 else ""))
            rows.append([disp, f2(sum(v) / len(v)) if v else "---"] + cells)
        w(table("PRISM components vs.\\ human labels (Spearman $\\rho$, item score = mean of 3 "
                "annotators; $^{*}$ permutation $p<0.05$, uncorrected). Mean: average metric value "
                "over the matched items. 3a: Step~3a accuracy; S3/S5 rt.: step ratings; "
                "S5 grd.: verdict follows directly; Chain: sum of the five mean step ratings.",
                "tab:prism-comp", "lc" + "c" * len(hl),
                ["\\textbf{Metric}", "Mean"] + [h for _, h in hl], rows))
        # by model
        rows = []
        for m in models:
            mi = [it for it in items if it["model"] == m]
            row = [mname(m), str(len(mi))]
            for col in ("PRISM", "L", "SC", "patom_score"):
                v = [meta_value(it, col) for it in mi if meta_value(it, col) is not None]
                row.append(f2(sum(v) / len(v)) if v else "---")
            rows.append(row)
        w(table("Mean trajectory metrics of the annotated items by model.", "tab:prism-model",
                "lccccc", ["\\textbf{Model}", "$n$", "PRISM", "$L$", "SC", "\\patom{} score"], rows))
    if not any(avail[c] for c in ("L", "delta3", "SC", "PRISM")):
        w(na_box("None of $L$, $\\Delta_3$, SC, PRISM are in the export. Supply them via "
                 "\\texttt{--meta} (columns \\texttt{L, delta3, SC, PRISM}) to fill Table~\\ref{tab:corr-new}; "
                 "the primary test is Step~3a $\\times$ $\\Delta_3$ ($\\rho>0.30$, $p<0.05$)."))
    w("\\paragraph{Supplementary: within-chain label correlations.} As an internal-consistency "
      "check computable now, Table~\\ref{tab:corr-internal} correlates human labels with each other. "
      "Because majority labels are near-constant (e.g.\\ Step~5 grounding is \\texttt{Yes} for every item), "
      "each item is scored by the \\emph{mean} of its three annotators' ordinal codes. A positive Step~3a $\\times$ Step~5 correlation is "
      "expected if verdict quality depends on the latitude step.\n")
    rows = []
    for (a_, an, b_, bn) in [("s3_correct", "Step 3a (ordinal)", "s5_follows", "Step 5 grounding"),
                             ("s3_correct", "Step 3a (ordinal)", "s5_rating", "Step 5 rating"),
                             ("s3_rating", "Step 3 rating", "s5_rating", "Step 5 rating"),
                             ("s1_rating", "Step 1 rating", "s3_correct", "Step 3a (ordinal)"),
                             ("s4_rating", "Step 4 rating", "s5_rating", "Step 5 rating")]:
        res = spearman([it["mean"][a_] for it in items], [it["mean"][b_] for it in items], rng)
        rows.append([an, bn, f2(res["rho"]), fp(res["p"]), str(res["n"])])
    w(table("Spearman correlations among human step labels (item score = mean of 3 annotators; "
            "permutation $p$).", "tab:corr-internal",
            "llccc", ["\\textbf{Label A}", "\\textbf{Label B}", "$\\rho$", "$p$", "$n$"], rows))

    # ================================================================ PHASE 6
    w("\\section{Phase 6 --- Failure Mode Analysis}\\label{sec:p6}\n")
    w("\\subsection{6.1 Frequency by model}\n")
    rows = []
    for code, desc in FAILURE_MODES.items():
        cells = []
        for m in models + ["ALL"]:
            mi = [it for it in items if m == "ALL" or it["model"] == m]
            nn = sum(n["code"] == code for n in notes if m == "ALL" or n["item"]["model"] == m)
            ni = sum(code in it["fmodes"] for it in mi)
            cells.append(f"{nn} / {ni} ({pct(ni, len(mi), 0)})")
        rows.append([code, desc] + cells)
    any_i = ["", "\\textbf{Any failure note}"]
    for m in models + ["ALL"]:
        mi = [it for it in items if m == "ALL" or it["model"] == m]
        k = sum(bool(it["fmodes"]) and it["fmodes"] != ["OT"] for it in mi)
        any_i.append(f"--- / {k} ({pct(k, len(mi), 0)})")
    rows += ["MIDRULE", any_i]
    w(table("Failure modes coded from annotator notes, by model. Cells: notes / items "
            "(\\% of items with $\\ge$1 such note). F1--F3 are the paper's taxonomy; E1--E6 are "
            "emergent categories; ``Any failure note'' excludes OT.", "tab:fm",
            "lp{5.6cm}" + "c" * (len(models) + 1),
            ["\\textbf{Code}", "\\textbf{Failure mode}"] + [f"\\textbf{{{mname(m)}}}" for m in models]
            + ["\\textbf{All}"], rows, size="\\footnotesize"))
    tot_fail_notes = sum(n["code"] != "OT" for n in notes)
    top = Counter(n["code"] for n in notes if n["code"] != "OT").most_common(3)
    w("Of the " + str(len(notes)) + f" notes, {tot_fail_notes} describe a model reasoning failure. "
      "The most frequent codes are " + ", ".join(f"{c} ({FAILURE_MODES[c]}; {k} notes)" for c, k in top)
      + ".\n")
    if len(models) == 2:
        c = [[sum(bool(it["fmodes"]) and it["fmodes"] != ["OT"] for it in items if it["model"] == m),
              sum(not (bool(it["fmodes"]) and it["fmodes"] != ["OT"]) for it in items if it["model"] == m)]
             for m in models]
        w(f"Fisher exact test (item has any failure note, {mname(models[0])} vs.\\ {mname(models[1])}): "
          f"$p={fp(fisher_exact_2x2(c[0][0], c[0][1], c[1][0], c[1][1]))}$.\n")
    if not avail["comment_type"]:
        w(na_box("Breakdown by comment type requires \\texttt{comment\\_type}."))
    else:
        rows = []
        for code, desc in FAILURE_MODES.items():
            rows.append([code] + [str(sum(code in it["fmodes"] for it in items
                                          if meta_value(it, "comment_type") == t)) for t in types])
        w(table("Items with each failure mode by comment type.", "tab:fm-type", "lccc",
                ["\\textbf{Code}", "P", "H", "E"], rows))

    w("\\subsection{6.2 Failure mode $\\times$ \\patom{} final score}\n")
    if avail["patom_score"]:
        rows = []
        for code, desc in FAILURE_MODES.items():
            res = spearman([float(code in it["fmodes"]) for it in items],
                           [meta_value(it, "patom_score") for it in items], rng)
            rows.append([code, desc, f2(res["rho"]) if res else "---", fp(res["p"]) if res else "---"])
        w(table("Point-biserial (Spearman) correlation of failure-mode presence with \\patom{} score.",
                "tab:fm-score", "lp{6cm}cc", ["\\textbf{Code}", "\\textbf{Mode}", "$\\rho$", "$p$"], rows))
    else:
        w(na_box("The \\patom{} final score is not in the export (supply \\texttt{patom\\_score} via "
                 "\\texttt{--meta}). Supplementary: failure-mode presence against the human Step~5 "
                 "grounding label is given below."))
        rows = []
        for code, desc in FAILURE_MODES.items():
            if code == "OT":
                continue
            with_ = [it for it in items if code in it["fmodes"]]
            without = [it for it in items if code not in it["fmodes"]]
            if not with_:
                continue
            res = spearman([float(code in it["fmodes"]) for it in items],
                           [it["mean"]["s5_follows"] for it in items], rng)
            rows.append([code, str(len(with_)),
                         f2(sum(it["mean"]["s5_follows"] for it in with_) / len(with_)),
                         f2(sum(it["mean"]["s5_follows"] for it in without) / len(without)),
                         f2(res["rho"]) if res else "---", fp(res["p"]) if res else "---"])
        w(table("Failure-mode presence vs.\\ Step~5 grounding (item score = mean of 3 annotators' "
                "ordinal codes, 0--2). Means for items with and without the mode; $\\rho$ = "
                "point-biserial (Spearman) with permutation $p$. Partly circular: annotators who "
                "downgrade a step are also the ones who write the note.",
                "tab:fm-s5", "lccccc", ["\\textbf{Code}", "$n_{\\text{items}}$", "Mean (with)",
                                        "Mean (without)", "$\\rho$", "$p$"], rows))

    w("\\subsection{6.3 Cross-validation against agreed-wrong items}\n")
    if avail["agreed_wrong"]:
        aw = [it for it in items if meta_value(it, "agreed_wrong") in (1.0, "1", "True", "true")]
        k = sum(bool(it["fmodes"]) and it["fmodes"] != ["OT"] for it in aw)
        w(f"{len(aw)} items are agreed-wrong in \\citet{{CITATION_PATOM}}; {k} ({pct(k, len(aw))}) "
          "carry at least one failure note.\n")
    else:
        w(na_box("Agreed-wrong flags from \\citet{CITATION_PATOM} are not in the export "
                 "(supply \\texttt{agreed\\_wrong} via \\texttt{--meta})."))

    # ================================================================ PHASE 7
    w("\\section{Phase 7 --- Profile Grounding Analysis (Step 3b)}\\label{sec:p7}\n")
    w(na_box("Step~3b (profile-grounded / text-only / mixed / cannot determine) was not collected "
             "in this annotation round, so neither 7.1 (grounding rate by model; H: GPT-5 $>$ Claude "
             "$>$ Qwen) nor 7.2 (Step~3b $\\times$ Step~3a accuracy) can be computed. The Step~3a "
             "accuracy by model needed for 7.2 is already reported in Table~\\ref{tab:3a-model}."))

    # ================================================================ APPENDIX
    w("\\appendix\n\\section{Verification of the paper's confirmed pilot numbers}\\label{app:pilot-check}\n")
    w("\\paper{Confirmed Pilot Numbers} table lists ``confirmed'' pilot statistics. Each is recomputed "
      "here from the export.\n")

    def ann_pct(a, fid, lab):
        return 100.0 * sum(get_label(it, a, fid) == lab for it in items) / N

    def ann_triplet(fid, lab, who=ANNOTATORS):
        return "/".join(f"{ann_pct(a, fid, lab):.0f}" for a in who) + "\\%"

    s1_same = sum(len({get_label(it, a, "s1_rating") for a in ANNOTATORS}) == 1 for it in items)
    pooled_yes = sum(get_label(it, a, "s3_correct") == "Yes" for it in items for a in ANNOTATORS)
    checks = [
        ("Total items", "50", str(N)),
        ("Claude Sonnet 4.6", "$n=21$", f"$n={sum(it['model']=='claude' for it in items)}$"),
        ("GPT-5", "$n=29$", f"$n={sum(it['model']=='gpt5' for it in items)}$"),
        ("Step 3a 3-way agreement", "86.0\\%",
         f"{pct(iaa['s3_correct']['exact']*100,100)} (correct); {pct(iaa['s3_class']['exact']*100,100)} (class.)"),
        ("Step 3a within-lat.\\ (A1/A2/A3)", "76/70/76\\%", ann_triplet("s3_class", "Within latitude")),
        ("Step 3a ``contrast error'' (A1/A2/A3)", "14/22/16\\%", ann_triplet("s3_class", "Contrast")),
        ("Step 3a ``assimilation'' (A1/A2/A3)", "10/8/8\\%", ann_triplet("s3_class", "Assimilation")),
        ("Step 3a correct (A1/A2[/A3])", "84\\%/84\\%", ann_triplet("s3_correct", "Yes")),
        ("Step 3a correct, pooled", "84\\%", pct(pooled_yes, 3 * N)),
        ("Step 5 verdict follows (A1)", "94\\%", f"{ann_pct('A1','s5_follows','Yes'):.0f}\\%"),
        ("Step 5 new reasoning (A1)", "4\\%", f"{ann_pct('A1','s5_newreason','Yes'):.0f}\\%"),
        ("Step 1 rating$=2$ (A1)", "98\\%", f"{ann_pct('A1','s1_rating','2'):.0f}\\%"),
        ("Step 5 rating$=2$ (A1)", "92\\%", f"{ann_pct('A1','s5_rating','2'):.0f}\\%"),
        ("Step 1 items rated identically", "49/50", f"{s1_same}/{N}"),
    ]
    w(table("Paper pilot statistics vs.\\ recomputed values.", "tab:pilot-check", "p{5.4cm}p{2.2cm}p{5.4cm}",
            ["\\textbf{Metric}", "\\textbf{Paper}", "\\textbf{Recomputed}"],
            [[a, b, c] for a, b, c in checks]))
    w("\\textbf{Note on terminology.} The paper labels the per-annotator Contrast/Assimilation "
      "shares as ``contrast error'' and ``assimilation'' rates. In the export these are the "
      "\\emph{classification the model used} (\\texttt{classification\\_used}), not errors; "
      "whether that classification was right is recorded separately in "
      "\\texttt{is\\_classification\\_correct}. Error rates in this report (Table~\\ref{tab:3a-model}) "
      "use the latter.\n")

    w("\\section{Coded annotator notes}\\label{app:notes}\n")
    w("\\begin{footnotesize}\n\\begin{longtable}{p{0.4cm}p{1.1cm}p{1.3cm}p{0.5cm}p{0.6cm}p{10.2cm}}\n"
      "\\toprule\n\\textbf{\\#} & \\textbf{Model} & \\textbf{Post} & \\textbf{Ann.} & \\textbf{Step} & "
      "\\textbf{Code --- note} \\\\\n\\midrule\\endhead\n")
    for i, n in enumerate(notes, 1):
        w(f"{i} & {tex(n['item']['model'])} & {tex(n['item']['post_id'])} & {n['annotator']} & "
          f"{n['step'][-1]} & \\textbf{{{n['code']}}} --- {tex(n['text'])} \\\\\n")
    w("\\bottomrule\n\\end{longtable}\n\\end{footnotesize}\n")

    w("\\section{Reproducibility}\n")
    w(f"Generated by \\texttt{{patom\\_bench\\_analysis.py}} (Python {sys.version.split()[0]}, standard "
      f"library only). Random seed {SEED}; {N_PERM:,} permutations for permutation tests; "
      f"{N_BOOT:,} bootstrap resamples for $\\alpha$ CIs. Command:\n\n"
      "\\begin{verbatim}\n" + "python3 patom_bench_analysis.py "
      + " ".join(["--data"] + [os.path.basename(p) for p in args.data]
                 + (["--meta", os.path.basename(args.meta)] if args.meta else [])
                 + ["--out", os.path.basename(args.out)]) + "\n\\end{verbatim}\n")
    w("\\end{document}\n")

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print(f"Wrote {args.out}  ({N} items, {len(notes)} notes, {len(shared)} shared pairs)")


PREAMBLE = r"""% Auto-generated by patom_bench_analysis.py --- do not edit by hand.
\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{times}
\usepackage[margin=0.9in]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage[table]{xcolor}
\usepackage{enumitem}
\usepackage{caption}
\usepackage{float}
\usepackage{mdframed}
\usepackage[hidelinks]{hyperref}
\definecolor{rowgray}{HTML}{EBF3FA}
\definecolor{warnbg}{HTML}{FFF3CD}
\newcommand{\patom}{\textsc{PAToM}}
\newcommand{\pbench}{\textsc{PAToM-Bench}}
\newcommand{\citet}[1]{[\texttt{\detokenize{#1}}]}
\newcommand{\paper}[1]{the paper's \emph{#1}}
\renewcommand{\arraystretch}{1.15}
\captionsetup{font=small,labelfont=bf}
\title{\pbench{}: Results of the Appendix~A Analysis Plan\\[2pt]
\large Pilot annotation export ($n=50$)}
\author{}
\date{\today}
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", nargs="+", default=[DEFAULT_DATA], help="annotation JSON file(s)")
    ap.add_argument("--meta", default=None, help="optional item metadata CSV")
    ap.add_argument("--patom-metrics", nargs="*", default=DEFAULT_PATOM,
                    help="PaTom repo per-sample metrics JSONL(s) (default: patom_repo_metrics/*.jsonl)")
    ap.add_argument("--condition", default="chain",
                    help="PaTom condition whose metrics to match (chain = PAToM; default)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output .tex path")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
