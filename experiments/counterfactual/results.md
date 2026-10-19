# Step-3 counterfactual: results

## Target items: to_within − paraphrase (n = 7 items)

- **Primary:** mean within-item difference +0.43 points (bootstrap 95% CI +0.17 to +0.71).
- **Exact Wilcoxon signed-rank:** two-sided p = 0.0625 (W+ = 15, n = 5 non-zero differences of 7; smallest attainable p with n = 5 is 0.0625).
- **Delta-prediction flips vs paraphrase:** 0 of 7 items (0 in the expected direction).
- Secondary: edit − stored -0.09; paraphrase − stored -0.51.

| Item | Stored | Paraphrase scores | Edit scores | Paraphrase mean | Edit mean | Diff | Flip |
|---|---|---|---|---|---|---|---|
| 1otj7pk|no4x7oe|claude | 3 | 2 2 2 2 2 | 3 3 3 3 3 | 2.00 | 3.00 | +1.00 | no |
| 12a4eco|jeqh3bc|claude | 4 | 3 3 3 3 3 | 4 4 4 3 4 | 3.00 | 3.80 | +0.80 | no |
| t1e0go|hygrp3z|claude | 5 | 4 4 5 5 4 | 5 5 4 4 4 | 4.40 | 4.40 | +0.00 | no |
| kq762d|gi29gkn|claude | 6 | 6 6 6 6 6 | 7 6 6 6 6 | 6.00 | 6.20 | +0.20 | no |
| 1ewdslq|liycs35|claude | 3 | 2 2 2 2 2 | 3 2 3 3 3 | 2.00 | 2.80 | +0.80 | no |
| ubwcpp|i67n15h|claude | 1 | 1 1 1 1 1 | 2 1 1 1 1 | 1.00 | 1.20 | +0.20 | no |
| 8skv52|e10o3x9|claude | 3 | 3 3 3 3 3 | 3 3 3 3 3 | 3.00 | 3.00 | +0.00 | no |

## Reverse items: to_contrast − paraphrase (n = 7 items)

- **Primary:** mean within-item difference -1.31 points (bootstrap 95% CI -2.23 to -0.66).
- **Exact Wilcoxon signed-rank:** two-sided p = 0.0156 (W+ = 0, n = 7 non-zero differences of 7; smallest attainable p with n = 7 is 0.0156).
- **Delta-prediction flips vs paraphrase:** 2 of 7 items (2 in the expected direction).
- Secondary: edit − stored -1.11; paraphrase − stored +0.20.

| Item | Stored | Paraphrase scores | Edit scores | Paraphrase mean | Edit mean | Diff | Flip |
|---|---|---|---|---|---|---|---|
| 1dlyt3u|l9shm76|claude | 9 | 9 9 9 9 9 | 8 8 9 8 6 | 9.00 | 7.80 | -1.20 | no |
| 2p6y53|cmu3xmz|claude | 9 | 9 9 9 9 9 | 8 8 8 8 9 | 9.00 | 8.20 | -0.80 | no |
| altl91|efjefbu|claude | 9 | 9 9 9 9 9 | 9 9 9 8 9 | 9.00 | 8.80 | -0.20 | no |
| 5q3wh6|dcw4qag|claude | 8 | 8 8 8 8 8 | 7 7 7 7 7 | 8.00 | 7.00 | -1.00 | no |
| 1mdcvh|cc84ghp|claude | 7 | 7 6 7 6 6 | 6 5 6 6 6 | 6.40 | 5.80 | -0.60 | no |
| 1o8oslz|njzw2ah|claude | 7 | 8 8 8 8 8 | 4 4 5 4 4 | 8.00 | 4.20 | -3.80 | yes |
| 3izepf|cul8cco|claude | 7 | 8 8 8 8 8 | 6 6 7 7 6 | 8.00 | 6.40 | -1.60 | yes |

## Follow-up, targets with Step 4 regenerated: to_within − paraphrase (n = 7 items)

Step 4 is regenerated on the edited (or paraphrased) Step 3 and Step 5 on that new Step 4; repeat k of Step 5 uses repeat k of Step 4.

- **Primary:** mean within-item difference +0.79 points (bootstrap 95% CI +0.61 to +0.94).
- **Exact Wilcoxon signed-rank:** two-sided p = 0.0156 (W+ = 28, n = 7 non-zero differences of 7; smallest attainable p with n = 7 is 0.0156).
- **Delta-prediction flips vs paraphrase:** 0 of 7 items (0 in the expected direction).
- **Comparison with Step 4 fixed:** +0.43 (CI +0.17 to +0.71) with Step 4 fixed vs +0.79 (CI +0.61 to +0.94) with Step 4 regenerated; difference +0.36.

| Condition | Repeats attempted | Step 4 attempts | Retries | Dropped repeats | Failed checks (count; an attempt can fail several) |
|---|---|---|---|---|---|
| to_within | 35 | 42 | 7 | 1 (8skv52 r1) | length 4, score/rating 1, turn label 4, verdict language 1 |
| paraphrase | 35 | 39 | 4 | 0 | length 3, verdict language 1 |

| Item | Stored | Paraphrase scores | Edit scores | Paraphrase mean | Edit mean | Diff | Diff (Step 4 fixed) | Flip |
|---|---|---|---|---|---|---|---|---|
| 1otj7pk|no4x7oe|claude | 3 | 2 2 2 2 2 | 3 3 3 3 3 | 2.00 | 3.00 | +1.00 | +1.00 | no |
| 12a4eco|jeqh3bc|claude | 4 | 3 3 3 3 2 | 4 4 4 4 3 | 2.80 | 3.80 | +1.00 | +0.80 | no |
| t1e0go|hygrp3z|claude | 5 | 4 4 4 5 5 | 5 5 5 5 6 | 4.40 | 5.20 | +0.80 | +0.00 | no |
| kq762d|gi29gkn|claude | 6 | 6 5 6 6 6 | 6 7 6 6 6 | 5.80 | 6.20 | +0.40 | +0.20 | no |
| 1ewdslq|liycs35|claude | 3 | 2 2 2 2 2 | 3 3 3 3 3 | 2.00 | 3.00 | +1.00 | +0.80 | no |
| ubwcpp|i67n15h|claude | 1 | 1 1 1 1 1 | 2 2 2 2 1 | 1.00 | 1.80 | +0.80 | +0.20 | no |
| 8skv52|e10o3x9|claude | 3 | 3 3 3 3 3 | 3 4 3 4 | 3.00 | 3.50 | +0.50 | +0.00 | no |

## Noise and fidelity baseline (unedited reruns)

- Pooled within-item rerun SD: 0.22 points (n = 7 items).
- Mean offset of rerun mean from stored score: -0.54 points.

| Item | Stored | Rerun scores |
|---|---|---|
| 16nttuv|k1goduu|claude | 4 | 3 3 3 3 3 |
| nerkh7|gyhrw30|claude | 7 | 6 5 5 5 6 |
| 17b4ql9|k5h6fys|claude | 6 | 6 6 6 6 6 |
| ygn05q|iu9t67z|claude | 6 | 6 6 6 6 6 |
| ofdnn1|h4cnsig|claude | 7 | 7 7 7 7 8 |
| 6m1xlb|djyea2h|claude | 5 | 5 5 5 4 4 |
| 1082opa|j3q1s75|claude | 6 | 5 5 5 5 5 |
