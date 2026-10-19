# Fidelity gate (NOISE items, original Steps 1-4)

CLI 2.1.294 (Claude Code), requested model `claude-sonnet-4-6`, 5 repeats per item.

## Pre-set criteria

| Criterion | Value | Result |
|---|---|---|
| mean signed difference (rerun - stored) | -0.54 | reported |
| mean absolute difference | 0.60 | reported |
| share of reruns within +/-1 of stored (target >= 70%) | 91% | PASS |
| delta agreement, per-item mean rerun (target >= 80%) | 86% (6/7 items) | PASS |
| format: parseable score line in every output | 35/35 | PASS |

## Per item

| Item | Stored | Reruns | MAD | Within ±1 | Δ agree | Format | Model(s) |
|---|---|---|---|---|---|---|---|
| 16nttuv|k1goduu|claude | 4 | 3 3 3 3 3 | 1.00 | 1.00 | 1.00 | 5/5 | claude-haiku-5-5;claude-sonnet-4-6 |
| nerkh7|gyhrw30|claude | 7 | 6 5 5 5 6 | 1.60 | 0.40 | 0.00 | 5/5 | claude-haiku-5-5;claude-sonnet-4-6 |
| 17b4ql9|k5h6fys|claude | 6 | 6 6 6 6 6 | 0.00 | 1.00 | 1.00 | 5/5 | claude-haiku-5-5;claude-sonnet-4-6 |
| ygn05q|iu9t67z|claude | 6 | 6 6 6 6 6 | 0.00 | 1.00 | 1.00 | 5/5 | claude-haiku-5-5;claude-sonnet-4-6 |
| ofdnn1|h4cnsig|claude | 7 | 7 7 7 7 8 | 0.20 | 1.00 | 1.00 | 5/5 | claude-haiku-5-5;claude-sonnet-4-6 |
| 6m1xlb|djyea2h|claude | 5 | 5 5 5 4 4 | 0.40 | 1.00 | 1.00 | 5/5 | claude-haiku-5-5;claude-sonnet-4-6 |
| 1082opa|j3q1s75|claude | 6 | 5 5 5 5 5 | 1.00 | 1.00 | 1.00 | 5/5 | claude-haiku-5-5;claude-sonnet-4-6 |
