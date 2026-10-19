# ToMTrace

A diagnostic resource for auditing Theory-of-Mind (ToM) reasoning in LLM persuasion judges.
50 five-step reasoning chains (Claude Sonnet 4.6: 21, GPT-5: 29) for delta-earning
Reddit ChangeMyView comments, each labelled step by step by three independent annotators.

## Contents

| Path | What it is |
|---|---|
| `data/tomtrace.jsonl` | 50 items: Reddit IDs, judge, judge score, the five step outputs, all three annotators' labels (9 fields), notes with failure codes, majority labels, soft labels (annotator means; Dawid–Skene posteriors for Step 3 endorsement), and trajectory metrics (L, rho, SC, CG, CC, PRISM) |
| `annotation/guidelines_v1.md` | Annotator guidelines with decision rules, common errors, and a worked practice item |
| `annotation/schema.json` | Machine-readable schema and failure-code definitions |
| `code/rehydrate.py` | Rebuilds post and comment text from IDs via the Arctic Shift Reddit archive |
| `code/patom_bench_analysis.py` | IAA (kappa, alpha, AC1, exact agreement), label distributions, failure-mode coding rules |
| `code/tomtrace_cluster_stats.py` | Cluster-robust (by post) bootstrap CIs and permutation tests for all correlations, the PRISM ablation, detector AUCs, and alpha; writes soft labels |
| `code/tomtrace_detectors.py` | AUC of candidate detectors against human-flagged failures |
| `code/tomtrace_ds_strategies.py` | Dawid–Skene model of Step 3 endorsement labels |
| `code/encoder_robustness.py` | Recomputes trajectory metrics with alternative sentence encoders (needs sentence-transformers) |
| `code/tomtrace_extra_analysis.py` | Supporting functions: correlations, PRISM ablation, note diagnostics |

## Post and comment text

The dataset ships Reddit IDs, not the original post and comment text. To rebuild it:

```bash
python3 code/rehydrate.py data/tomtrace.jsonl data/tomtrace_rehydrated.jsonl
```

The script queries the public Arctic Shift archive (https://arctic-shift.photon-reddit.com) by ID and
needs only the Python standard library. In October 2026 it recovered all 50 items, matching the
annotated text exactly up to whitespace. Content deleted from the archive later is reported, not
silently dropped.

## Labels

Annotators were blind to delta status. Labels are independent Pass-1 labels; there was no adjudication.
The Step 3 field `is_classification_correct` records *annotator endorsement*: whether a lay reader finds the
judge's latitude inference supported by the post and comment. It is a plausibility judgment, not ground truth
and not the OP's actual latitude. Majority labels are operational summaries; prefer the soft labels and the
individual labels for analysis.
Majority labels are derived by 2-of-3 vote. There are three three-way ties (two items on the Step 3
rating, one on the Step 5 rating); they are recorded as `null` and resolved by the median of the three
codes in ordinal analyses.

## Intended use

Auditing and diagnosing judge reasoning, and validating automated reasoning metrics against human
judgment. Not intended as a training set or as a benchmark for ranking judges, and not for any system
that makes consequential decisions about individuals.
