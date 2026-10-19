# Step-3 counterfactual experiment (Claude Sonnet 4.6 chains)

Tests whether the Step-3 latitude call causes the Step-5 score: Step 3 is edited, Steps 1, 2
and 4 are kept, and only Step 5 is regenerated. No released file (data/, annotation/, code/)
is modified; everything lives in this directory.

## Files
| File | Purpose |
|---|---|
| `reconstruct.py` | Rebuilds the exact PAToM message list (raw PaTom outputs, original prompts, original truncation) |
| `select_items.py` → `items.csv` | Phase 1 item selection (7 target, 7 reverse, 7 noise; only 21 Claude chains exist) |
| `edits_spec.py`, `build_edits.py` → `step3_edits.csv`, `step3_edits_review.md`, `edit_checks.csv` | Phase 2 hand-drafted Step-3 edits and automatic checks |
| `verify_edits.py` → `edit_verification.csv` | Independent re-check of all edits, with reviewed exceptions |
| `cli_judge.py` | `call_judge(system, user_text, cache_key)`: CLI wrapper with caching to `raw/` |
| `fidelity_gate.py` → `fidelity_gate.csv/.md` | Fidelity gate on the noise items |
| `prompt_template.txt` | Flattened-transcript template |

## How judge calls are made
No API key is available, so calls go through the Claude Code CLI in headless mode using the
logged-in subscription.

- CLI version: `2.1.294 (Claude Code)`
- Command: `claude -p --output-format json --model claude-sonnet-4-6 --tools '' --safe-mode --no-session-persistence --system-prompt <PAToM system prompt>` (user message on stdin)
- Requested model: `claude-sonnet-4-6`. The judge's answer comes from `claude-sonnet-4-6` in every call so far. The CLI
  also sends each prompt to `claude-haiku-5-5` for its own housekeeping (about 5.4k input, 25 output tokens,
  not every call); this does not produce the judge output. Both models and their token usage are recorded
  per call in `raw/*.json`. No documented `--help` flag disables this side call.
- Environment: `ANTHROPIC_API_KEY` removed; `{'MAX_THINKING_TOKENS': '0'}` set so Sonnet uses no extended thinking
  (the CLI default enables it; the original chains were plain API calls). This is an environment variable,
  not a `--help` flag; a probe confirmed it yields 0 thinking tokens.
- Calls run from the empty directory `_cli_sandbox/`; `--safe-mode` disables CLAUDE.md, skills, plugins, hooks
  and MCP servers; `--tools ""` disables all tools; `--no-session-persistence` keeps sessions off disk.
- Every call is cached to `raw/<key>.json` (input, output, models, usage, CLI version, flags, timestamp) and
  resumed from cache; calls are spaced at least 3 s apart; a usage-limit message stops the run cleanly.
- Scores are parsed with the repo parser (last `Score: N`, kept if 1–10); parse failures are logged, not guessed.

### Caveats
- **Default sampling.** The CLI exposes no temperature or max-token control, so calls use the CLI's default
  sampling instead of the original temperature 0.2 and 768-token cap.
- **Flattened transcript.** The CLI cannot inject prior assistant turns, so the five-turn conversation is
  rendered as one user message (template below), unlike the original multi-turn API calls.
- **Fixed CLI overhead of ~615 input tokens.** A tiny call (system "You are terse.", user "Reply with exactly:
  OK", about 10 tokens) registers 625 Sonnet input tokens. Adding `--disable-slash-commands`,
  `--strict-mcp-config`, `--setting-sources ""`, or disabling tool search (`ENABLE_TOOL_SEARCH=false`) leaves it at
  625–628, so it is a fixed preamble the CLI adds that no documented flag removes. It is identical in every call
  and condition. A real judge call registers 3,675 Sonnet input tokens for a ~13k-character prompt.

## Edit review (before any edited-condition calls)

`verify_edits.py` re-checks every row of `step3_edits.csv` (written to `edit_verification.csv`): only
latitude sentences changed (rest of Step 3 byte-identical, and each replaced sentence is a latitude
sentence by a vocabulary check), length within ±15%, no new numbers, no new named entities or quoted phrases.

**24/28 rows passed all automatic checks.** One edit was corrected first: the `5q3wh6` paraphrase had
introduced a number word ("Neither of the two extremes applies here"), changed to "Neither extreme is
relevant here". The remaining **4 rows failed only the latitude-vocabulary check** and were **kept after
manual review, before any edited-condition calls were run** (`manual_override = yes` in
`edit_verification.csv`):

- `5q3wh6` `to_contrast` and `paraphrase`: the replaced sentences are latitude claims in Social Judgment
  Theory terms (credible, non-threatening distance; restating versus leaping to an incompatible worldview;
  ideal persuasive distance). The vocabulary check is too narrow for them.
- `ubwcpp` `to_within`: the replaced sentence states the consequence of the assimilation call; leaving it
  unchanged would make the edited Step 3 contradict itself.
- `ubwcpp` `paraphrase`: edits the same sentence as the `to_within` row, so both conditions change the
  same text.

## Flattened-transcript format
See `prompt_template.txt`. Fully rendered example (noise item `16nttuv|k1goduu|claude`, user message):

```
Below is a conversation in progress. Continue it by writing ONLY the assistant's response to the final user turn, following its instructions exactly.

[USER - Step 1]
### Step 1 of 5 — 1st-order OP: OP's belief state

**Post**
Title: CMV: Angel Hernandez is fine

I'm mostly not a baseball fan (though I go to a handful of minor league games every year). But from what I can tell, baseball fans think Angel Hernandez is the worst ump in the league by a huge margin. And the evidence of this is mostly compilations of bad calls he's made over the years. My view is that probably, Hernandez is an average ump that's become a scapegoat. He's missed some calls over the course of his career -- probably a lot of calls -- but presumably they all miss calls from time to time. Those compilations could have been made for practically any ump that's been in the game as long has he has.

Original poster (OP) — ToM (Beliefs, Desires, Intentions, Knowledge, Perspective-Taking):
  Beliefs: [Average, Scapegoat] — Hernandez is an average umpire wronged by public scrutiny due to compilation of calls.
  Desires: [Fairness, Balance] — A more level assessment of umpires' performance, especially long-tenured ones.
  Intentions: [Perception, Correction] — Encourage others to view Hernandez as representative of average umpiring, not uniquely bad.
  Knowledge: [awareness, skepticism] — The author acknowledges limited knowledge of baseball but is skeptical of the reliability of compilation videos as evidence of incompetence, suggesting such clips could apply to any long-tenured umpire.
  Perspective-Taking: [impartiality, understanding] — The author considers the broader fan perspective, recognizing that while collected calls may paint Hernandez in a bad light, they’re likely representative of normal human error and not unique to him.

Answer in 3–5 sentences:
1. What does the OP actually believe, and what position are they defending?
2. What are the **load-bearing assumptions** underneath their stated view — the premises they treat as self-evident that a challenger would need to undermine?

Do not mention the comment yet — it has not been shown.

[ASSISTANT - Step 1]
## Step 1: OP's Belief State

**What the OP believes and defends:** The OP believes that Angel Hernandez is likely an average umpire who has been unfairly scapegoated by baseball fans. They are defending the position that the compilation videos used as evidence of his incompetence are misleading, because any long-tenured umpire would accumulate enough bad calls to produce a similarly damning highlight reel. Being a casual fan, they are skeptical of the fan consensus and frame it as a kind of mob mentality or confirmation bias rather than a legitimate data-driven conclusion.

**Load-bearing assumptions:**
1. **Compilation videos are not meaningful evidence** — they assume that cherry-picked bad calls are an unreliable metric because survivorship/selection bias makes any ump look bad over a long career.
2. **All umpires miss calls at roughly comparable rates** — they implicitly assume there is no meaningful performance distribution among MLB umpires, i.e., that Hernandez is not a statistical outlier.
3. **Fan consensus is driven by emotion/scapegoating rather than data** — they treat the widespread negative reputation as a social phenomenon rather than a signal grounded in observable performance differences.
4. **Longevity explains the volume of bad calls** — they assume the sheer number of years in the league, not unusual error frequency, accounts for the volume of documented mistakes.

[USER - Step 2]
### Step 2 of 5 — 1st-order Commenter: commenter's argument and epistemic stance

Comment author — ToM (Beliefs, Desires, Intentions):
  Beliefs: [Professionalism, Fairness] — Hernandez is not just statistically below par but behaves in a manner that is personally antagonistic and unprofessional during games.
  Desires: [Accountability, Composure] — The author values umpires who conduct themselves with emotional control and effective professionalism in high-pressure environments.
  Intentions: [Persuasion, Normative Change] — The author intends to influence readers to reconsider Hernandez’s competence not just on the field but in maintaining respectful conduct.

**Comment being evaluated**
An ump who is ‘fine’ isn’t great but it’s more than just the stats it’s his manner during games of being definitely bad and taking everything personally.

Answer in 3–5 sentences:
1. What is the commenter's core argument or counter-position?
2. What is their own epistemic stance — what do *they* believe, and from what perspective are they arguing?

[ASSISTANT - Step 2]
## Step 2: Commenter's Argument and Epistemic Stance

**Core argument:** The commenter's counter-position is that Hernandez's problems extend beyond statistical performance metrics — his conduct and demeanor during games are themselves evidence of unfitness. Specifically, they argue that Hernandez takes criticism personally and behaves in an antagonistic or emotionally reactive way, which is a separate and additional dimension of incompetence beyond missed calls. The implicit claim is that "fine" requires not just adequate accuracy but also professional composure, and Hernandez fails on this second axis.

**Epistemic stance:** The commenter appears to be a baseball-engaged observer who treats Hernandez's behavioral patterns as well-established and observable facts, not merely fan perception. They are arguing from a normative framework about what professional umpiring requires — emotional neutrality and thick-skinnedness — and seem confident that Hernandez visibly and repeatedly violates this standard. Their perspective is that the OP's framing (focusing only on whether bad-call compilations are cherry-picked) misses an entire category of evidence, namely demeanor and interpersonal conduct, that independently justifies the negative reputation.

[USER - Step 3]
### Step 3 of 5 — Latitude of acceptance (Social Judgment Theory)

Comment author — perspective on OP — ToM (Perspective-Taking, Knowledge):
  Perspective-Taking: [Empathy, Critical Evaluation] — The author considers the broader perspective of game impact and fan perception, recognizing that Hernandez's behavior may affect others despite his statistical performance.
  Knowledge: [Observation, Personal Experience] — The author knows about Hernandez's conduct from direct observation during games, implying firsthand familiarity with his demeanor.

The OP's anchor position and load-bearing assumptions are established in Step 1. The commenter's argument is established in Step 2.

Social Judgment Theory (Sherif & Hovland, 1961) holds that persuasion succeeds only when an argument lands within the target's **latitude of acceptance** — the range of positions they would consider. Arguments too close to the anchor are assimilated (heard as agreement, no change); arguments too far are contrasted (rejected as extreme).

Answer in 3–5 sentences:
1. What is the OP's likely **latitude of acceptance** — how far from their anchor would they be willing to move, given their stated beliefs and reasoning style?
2. Does the commenter's argument land **within** that latitude — far enough to move the OP but not so discrepant it triggers rejection?
3. Or does it **assimilate** (essentially restates what the OP already believes) or **contrast** (positions itself so far from the anchor it would be dismissed)?

[ASSISTANT - Step 3]
## Step 3: Latitude of Acceptance

**OP's latitude of acceptance:** The OP has staked out a moderate, skeptical-but-open position — they're not a passionate Hernandez defender, just a casual observer pushing back on what they see as unfair mob consensus. This suggests a relatively wide latitude of acceptance; they would likely entertain arguments that present *systematic, non-cherry-picked evidence* of Hernandez's underperformance. However, they would probably resist arguments that simply reassert fan consensus or rely on subjective impressions, since their core epistemic commitment is to skepticism of emotionally-driven crowd judgment. They seem open to being shown they're wrong, but only through the kind of evidence that addresses their specific objection about selection bias.

**Does the commenter's argument land within that latitude?** The commenter's argument introduces a genuinely new dimension — professional conduct and demeanor — that the OP hadn't explicitly addressed, which gives it some potential traction. However, the argument is asserted rather than evidenced: phrases like "being definitely bad" and "taking everything personally" are stated as obvious facts without concrete examples, data, or incidents that would satisfy an epistemically skeptical reader.

**Assimilation or contrast?** The argument neither assimilates nor sharply contrasts — it occupies an awkward middle ground. It gestures toward a valid new category of evidence (behavioral professionalism) but delivers it too vaguely and assertively to move a skeptic who has already identified fan emotionalism as the problem. The OP would likely acknowledge the point as theoretically relevant but insufficient to shift their view without more grounding.

[USER - Step 4]
### Step 4 of 5 — 3rd-order (Commenter → OP → Commenter): credibility and intent management

OP — emotional register — ToM (Emotions):
  Emotions: [empathy, frustration] — The author feels empathy for Hernandez, seeing him as unfairly targeted, and expresses frustration with the public's harsh judgment of him.

Comment author — emotional stance — ToM (Emotions):
  Emotions: [Frustration, Disapproval] — The author feels frustration and disapproval toward Angel Hernandez's behavior, attributing personal offense and negative emotions to his on-field conduct.

Answer in 2–4 sentences:
1. Does the commenter's emotional stance acknowledge or match the OP's emotional register — showing genuine engagement rather than dismissal?
2. Do they signal **good faith** — intellectual respect, shared values, or intellectual humility before challenging the OP?
3. Does the commenter preemptively manage how the OP will perceive their credibility (e.g., conceding minor points, acknowledging the OP's strongest concern)?

[ASSISTANT - Step 4]
## Step 4: Credibility and Intent Management

**Emotional alignment:** The commenter's emotional stance — frustration and disapproval toward Hernandez — is essentially the opposite of the OP's empathy for him, and the commenter makes no effort to acknowledge or bridge this gap. Rather than validating the OP's concern about unfair scapegoating before pivoting to their counter-argument, the commenter jumps directly into assertion, which is likely to feel dismissive to an OP who has explicitly framed their view around fairness and impartiality.

**Good faith signaling:** The commenter offers minimal good faith scaffolding — there is no concession that the OP raises a legitimate point about compilation bias, no acknowledgment of shared values around fair evaluation, and no intellectual humility about the subjectivity of "manner" as evidence. The one partial exception is the opening phrase "An ump who is 'fine' isn't great," which loosely engages the OP's framing, but it reads more like a rhetorical setup than genuine acknowledgment.

**Credibility management:** The commenter does nothing to preemptively establish why their behavioral observations should be trusted over the OP's skepticism of fan consensus — they don't cite specific incidents, invoke any insider knowledge, or distinguish their perspective from the emotionally-driven crowd judgment the OP has already discounted. This is a significant credibility gap, because the OP's entire position is built on skepticism of exactly this kind of confident but unsubstantiated fan assertion.

[USER - Step 5]
### Step 5 of 5 — Verdict

Using your full nested analysis:
  • Step 1 — OP's beliefs and load-bearing assumptions
  • Step 2 — Commenter's argument and epistemic stance
  • Step 3 — Whether the argument lands within the OP's latitude of acceptance (SJT)
  • Step 4 — Whether the commenter managed OP's perception of their credibility/intent

Rate whether this comment is a **well-calibrated persuasive act toward this specific OP**.

Respond in **exactly** this format:
Reasoning: <2–3 sentences grounded in your chain-of-analysis above>
Score: <integer 1–10>
```

## Fidelity gate (noise items, original Steps 1–4)

7 noise items × 5 repeats = 35 calls (only 21 Claude chains exist, so 7 remain after the target and reverse groups). Criteria were fixed before the run.

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

Noise baseline: pooled within-item rerun SD 0.22 points; mean offset of the rerun mean from the stored score -0.54 points (reruns run slightly low). The one delta disagreement is `nerkh7` (stored 7, reruns 5–6).

## Results (edited conditions)

140/140 edited-condition calls completed (28 edits × 5 repeats; 175 calls in total including the gate), with no parse failures and no usage-limit stops. The full tables are in `results.md` and `results_items.csv`; the figure is `results_figure.svg`. The paraphrase condition is the anchor, so the −0.54 CLI offset cancels.

| Group (n = 7 items each) | Comparison | Mean within-item diff | Bootstrap 95% CI | Delta flips vs paraphrase |
|---|---|---|---|---|
| Targets | to_within − paraphrase | +0.43 | +0.17 to +0.71 | 0/7 |
| Reverse controls | to_contrast − paraphrase | −1.31 | −2.23 to −0.66 | 2/7 (both downward, as expected) |

Secondary, against stored scores: targets edit − stored −0.09, paraphrase − stored −0.51; reverse edit − stored −1.11, paraphrase − stored +0.20. Noise baseline: rerun SD 0.22, offset −0.54.

Reading: both effects point in the predicted direction and both CIs exclude zero, but they are asymmetric. Rewriting an assimilation or contrast call as within-latitude raises Step 5 by less than half a point and moves no item across the delta threshold. Rewriting a within-latitude call as contrast lowers Step 5 by about 1.3 points; the drop is driven mostly by `1o8oslz` (−3.8) and `3izepf` (−1.6), the only two flips. With 7 items per group, the CIs are wide, and the bootstrap over items does not account for the hand-written edits differing in strength.

## Follow-up: Step 4 regenerated (targets only)

Question: does the Step 3 edit move the score more when Step 4 is also regenerated on the edited Step 3 (rather than kept as stored)? Design: the 7 target items × {to_within, paraphrase} × 5 repeats; for each repeat, Step 4 is regenerated on the edited (or paraphrased) Step 3, then Step 5 on that new Step 4. Steps 1–2 stay as stored. Code: `run_step45.py`, `step4_check.py`; per-attempt log: `step4_attempts.csv`.

### Invalid first attempt (moved to `raw_invalid/`)

The first attempt used the Step-5-only prompt for the Step 4 call. In all 12 Step 4 outputs it produced, the model kept writing past Step 4: it echoed `[ASSISTANT - Step 4]`, invented a `[USER - Step 5]` turn, and in 5 cases wrote its own `[ASSISTANT - Step 5]`. That text was then given to the Step 5 call as "Step 4", so those Step 5 calls saw an invented turn (and sometimes an invented verdict). All 23 calls (12 Step 4, 11 Step 5) and their logs were moved to `raw_invalid/` and are not used. None of the 175 Step-5-only outputs (gate and edited conditions) contains an echoed turn marker.

### Rules (fixed before the rerun)

1. **Step 4 prompt.** The Step 4 call has one extra instruction, appended to the header, that is not used in the Step-5-only runs: *"Write ONLY the assistant's Step 4 answer, then stop: do not write any later turns or turn labels. End your answer with the line "END OF STEP 4"."* It is applied identically to both conditions (`STEP4_HEADER` in `cli_judge.py`). Step 5 calls use exactly the same header as the Step-5-only runs.
2. **Cut.** The Step 4 output is cut at "END OF STEP 4" or at the first echoed turn marker (`[USER - Step N]` / `[ASSISTANT - Step N]`), whichever comes first. A leading echo ending in `[ASSISTANT - Step 4]` within the first 200 characters is dropped. Nothing else is changed; no Step 4 is edited by hand or by any other heuristic.
3. **Validity check** (after the cut; `step4_check.check`). A Step 4 fails if any of:
   - length outside 600–2,500 characters (stored Claude Step 4 median 1,608);
   - a turn label: `[USER`, `[ASSISTANT`, `[STEP`, or any mention of Step 5 (back-references to Steps 1–3 are allowed, because stored Step 4s use them);
   - `Score:` or a numeric 1–10 rating (e.g. "7/10", "a score of 6", "earns a **3**");
   - verdict language: earn / award / win / receive / get a delta, final score / verdict / rating, delta-worthy;
   - a meta-response: an opening "Understood", "Okay", "Sure", "Got it", "Noted", "Certainly", "Note that this step", "I'll wait", or "I will hold" anywhere.

   Calibration before the rerun: on all 1,000 stored Claude Step 4 outputs the check fails 5 (0.5%), all for delta-earning phrases; on the 12 invalid first-attempt outputs it passes the 9 that, after the cut, are ordinary Step 4 answers (1,519–1,793 characters) and fails the 3 that are not (a meta-note, "Understood — I will hold…", and a scrambled reply). Two rules were narrowed during this calibration, before any rerun: back-references to Steps 1–3 and the bare word "verdict" no longer count.
4. **Retry.** A Step 4 that fails the check is regenerated, up to 3 attempts. If all 3 fail, that repeat is dropped for that item and recorded. The rule is the same for both conditions; every attempt is cached and logged in `step4_attempts.csv`.
5. **Step 5 input assertion.** Before each Step 5 call, its input must contain exactly the real turn markers (`[USER - Step 1]` … `[ASSISTANT - Step 4]`, `[USER - Step 5]`, once each, in order) and no "END OF STEP 4"; otherwise the call is aborted.
6. **Pilot, then full run.** Pilot: 2 target items × both conditions × repeat 0 (8 calls plus any retries), reviewed before the full run. Full run: 7 items × 2 conditions × 5 repeats × 2 steps = 140 calls plus retries (pilot calls are reused from the cache); the run stops if all follow-up calls, including retries, would exceed 180.
7. **Analysis.** Same as the primary analysis: to_within − paraphrase per item (mean over the valid repeats), bootstrap 95% CI over items, exact Wilcoxon signed-rank p, delta flips; plus retries and dropped repeats per condition, compared with the Step-4-fixed result (+0.43).

### Results (follow-up)

All 70 repeats were attempted (8 pilot calls reused); 150 follow-up calls in total (140 planned, plus 11 Step 4 retries, minus the Step 5 call skipped for the dropped repeat), under the 180 cap. No usage-limit stop, no Step 5 parse failure, no Step 5 input assertion failure.

| | to_within | paraphrase |
|---|---|---|
| Step 4 attempts | 42 | 39 |
| Retries | 7 | 4 |
| Dropped repeats | 1 (`8skv52` r1: all 3 attempts were empty or a placeholder label) | 0 |

9 of the 11 failed attempts are on `8skv52`, where the model often wrote only a placeholder (empty, "[continued]", "[Fill in Step 4 here.]") before "END OF STEP 4", or a bracketed label above a normal answer. The other 3 were ordinary Step 4s rejected for one phrase ("9/10", "delta-worthy", "awarding a delta").

| | Step 4 fixed (stored) | Step 4 regenerated |
|---|---|---|
| to_within − paraphrase, mean over 7 items | +0.43 (95% CI +0.17 to +0.71) | **+0.79** (95% CI +0.61 to +0.94) |
| Exact Wilcoxon, two-sided | p = 0.0625 (5 non-zero of 7) | p = 0.0156 (7 non-zero of 7, all positive) |
| Delta flips vs paraphrase | 0 of 7 | 0 of 7 |

Reading: letting Step 4 follow the edited Step 3 roughly doubles the effect of the latitude edit on the Step 5 score (difference +0.36), and every item now moves upward, but no target item crosses the delta threshold. Caveats: the Step 4 call has an extra instruction not used in the Step-5-only runs (identical across conditions); `8skv52` has 4 edit repeats instead of 5; 7 items.
