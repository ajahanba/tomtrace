#!/usr/bin/env python3
"""
Recompute PAToM trajectory metrics for the 50 ToMTrace chains with different
sentence encoders (run inside an environment with sentence-transformers).

Step texts and source text follow PaTom/evaluation/metrics/eval_comprehensive.py:
steps = step1..step4 outputs + final reasoning; source = post_analysis + comment_analysis.
Metric formulas follow PaTom/evaluation/eval/metrics.py.

Output: encoder_metrics.json  {encoder: {item_key: {L, rho, SC, CG, CC, PRISM}}}
"""

import json
import os

import numpy as np
from sentence_transformers import SentenceTransformer

HERE = os.path.dirname(os.path.abspath(__file__))
ENCODERS = ["all-MiniLM-L6-v2", "all-mpnet-base-v2"]


def cos(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na and nb else 0.0


def metrics(pts, src):
    d = np.diff(pts, axis=0)
    L = float(np.sum(np.linalg.norm(d, axis=1)))
    rho = float(np.mean([cos(d[i], d[i + 1]) for i in range(len(d) - 1)]))
    sc = float(np.mean([cos(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]))
    cg = cos(pts[-1], src)
    cc = cos(pts[-1], pts.mean(axis=0))
    prism = L * (-rho) * sc * (cg * cc) ** 0.5 if cg >= 0 and cc >= 0 else float("nan")
    return {"L": L, "rho": rho, "SC": sc, "CG": cg, "CC": cc, "PRISM": prism}


def main():
    ann = json.load(open(os.path.join(HERE, "MSO222_PersuasionReasoningAnnotation_50.json")))
    pairs = {(p["post_id"], p["comment_id"]): p for p in
             json.load(open(os.path.join(HERE, "PaTom", "data", "benchmark", "cmv_tom_pairs_1000.json")))["pairs"]}
    chains = {}
    for m in ("claude", "gpt5"):
        for line in open(os.path.join(HERE, "PaTom", "results", "sample_outputs", f"chain_fullrubric_{m}_1000.jsonl")):
            r = json.loads(line)
            chains[(r["post_id"], r["comment_id"], m)] = r
    texts, keys = [], []
    for x in ann:
        k = (x["post_id"], x["comment_id"], x["model"])
        r = chains[k]
        final = r.get("reasoning") or r.get("raw_response", "")
        steps = [r.get(f"step{i}_output", "") or "" for i in range(1, 5)] + [final]
        p = pairs[k[:2]]
        src = (p.get("post_analysis", "") + " " + p.get("comment_analysis", "")).strip()
        keys.append("|".join(k))
        texts.append(([s.strip() for s in steps], src))
    out = {}
    for enc in ENCODERS:
        model = SentenceTransformer(enc)
        res = {}
        for key, (steps, src) in zip(keys, texts):
            e = model.encode(steps + [src], convert_to_numpy=True, normalize_embeddings=False)
            res[key] = metrics(e[:-1].astype(np.float64), e[-1].astype(np.float64))
            res[key]["unit_norm_max_dev"] = float(np.max(np.abs(np.linalg.norm(e, axis=1) - 1)))
        out[enc] = res
        print(enc, "done")
    json.dump(out, open(os.path.join(HERE, "encoder_metrics.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
