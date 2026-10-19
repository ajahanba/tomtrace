# Annotation Guidelines: Chain-of-ToM Reasoning Correctness

## Content Note

This dataset is drawn from a QA forum/ChangeMyView, a community for structured civil debate. About 42% of items cover entirely neutral topics (e.g. seatbelt laws, cereal taxonomy, unpaid internships). The remainder touch on politically or socially charged subjects typical of that forum — most commonly race and racism (~22% of items), religion (~18%), and political ideology including references to Nazism and communism as historical or political topics (~9%).

You will not encounter graphic descriptions, slurs, or content designed to harm — those items have been removed. The debates are substantive but civil in register.

**Your task is to evaluate the AI's reasoning, not the political content itself.** You do not need to have or express a view on any of the topics debated.

If an item causes you discomfort, skip it and note the item ID — you will not be penalised.

---

## Purpose

You are evaluating the reasoning quality of an AI judge that assesses whether a comment (i.e., answer) is persuasive toward a specific original poster (OP). The judge reasons in four steps before issuing a verdict. Your job is to annotate **each step independently** for correctness — not to judge whether the comment is persuasive yourself.

---

## What You Will See Per Item

Each item contains:

| Field | What it is |
|---|---|
| `post_title` + `post_text` | The original Reddit post (ChangeMyView) — read this first |
| `comment_text` | The comment the judge is evaluating |
| `step1_output` | Judge's characterisation of the OP's beliefs |
| `step2_output` | Judge's characterisation of the commenter's argument |
| `step3_output` | Judge's assessment of whether the argument could move the OP |
| `step4_output` | Judge's assessment of the commenter's tone and credibility signals |
| `step5_output` | Judge's final reasoning summary — the verdict that follows from Steps 1–4 (score withheld) |
| `model` | Which AI produced the reasoning (`gpt5` or `claude`) — ignore for annotation |

**Read the post and comment in full before annotating any step.**

---

## The Five Reasoning Steps — What Each Should Do

### Step 1 — OP's Belief State

The judge should identify:
- The **core claim** the OP is defending (what position are they trying to hold?)
- The **load-bearing assumptions**: premises the OP treats as self-evident, which if challenged would undermine their position
- The OP's **emotional register** or motivations (why do they care?)

A correct Step 1 is grounded strictly in the post text. It does not invent positions the OP did not take.

### Step 2 — Commenter's Argument

The judge should identify:
- The commenter's **counter-position** (what are they arguing?)
- Their **epistemic stance** (are they arguing from evidence, values, analogy, lived experience, speculation?)
- Whether they **directly address** the OP's topic or argue about something adjacent

A correct Step 2 faithfully represents what the comment actually says. It does not read in intent the comment does not express.

### Step 3 — Latitude of Acceptance

This is the most important step. The judge should assess:
- Does the comment's argument **target a load-bearing assumption** from Step 1?
- Is the argument **within the OP's latitude of acceptance** — close enough to be considered, different enough to cause reconsideration?
  - **Assimilation**: the comment is so close to the OP's view it is heard as agreement — no movement
  - **Contrast**: the comment is so far from the OP's view it is dismissed outright — no movement
  - **Within latitude**: the comment challenges the OP at a point where they could genuinely update — persuasion possible
- Does the judge's classification (assimilation / contrast / within latitude) match the actual relationship between the post and comment?

### Step 4 — Credibility and Tone Management

The judge should assess:
- Does the commenter **acknowledge the OP's concerns** emotionally, or do they dismiss/ignore them?
- Do they signal **good faith** (concessions, shared values, respect)?
- Do they **establish credibility** in a way the OP would find relevant (expertise, evidence, intellectual humility)?

A correct Step 4 is based on what is actually in the comment, not on ideal rhetoric.

### Step 5 — Final Verdict

The judge should synthesise Steps 1–4 into a coherent verdict explaining why the comment is or is not persuasive for this specific OP. The final score has been withheld; you are only evaluating whether the **reasoning** in Step 5 follows from the chain.

The judge should:
- Draw on the latitude-of-acceptance finding from Step 3 as the primary driver
- Acknowledge Step 4 factors (tone, credibility) as secondary modifiers
- Not introduce new claims or reversals not supported by the prior steps

A correct Step 5 is internally consistent with the chain — it does not change direction without justification.

---

## Annotation Scale

Rate each step on a **0–2 scale**:

| Rating | Label | Definition |
|---|---|---|
| **2** | Correct | The judge's characterisation accurately captures the key content; a reasonable reader of the same post/comment would agree |
| **1** | Partially correct | Captures some key content but misses an important aspect, overstates something, or adds a claim not clearly supported by the text |
| **0** | Incorrect | Significantly mischaracterises the post or comment, invents content not present, or misidentifies the core claim/argument |

---

## Step-by-Step Annotation Guidance

### Annotating Step 1

Ask yourself:
1. Is the OP's core claim correctly identified? (Not a paraphrase of the title — the actual argumentative position)
2. Are the load-bearing assumptions real? Could you point to a sentence in the post that supports each one?
3. Is anything invented or projected onto the OP that they did not express?

**Rate 2** if the substance is right even if the wording differs from how you'd phrase it.  
**Rate 1** if the core claim is right but an important assumption is missed or distorted.  
**Rate 0** if the judge describes a different position than the one the OP actually holds.

### Annotating Step 2

Ask yourself:
1. Is the commenter's main argument correctly identified?
2. Is the epistemic stance (how they argue) accurate — e.g., does the judge say "empirical evidence" when the comment is actually speculation?
3. Does the judge over-interpret — attributing intent or nuance not present in the comment?

**Rate 2** if the argument and stance are faithfully represented.  
**Rate 1** if the main argument is right but the stance is mischaracterised, or a significant sub-argument is ignored.  
**Rate 0** if the judge describes a different argument than the one actually made.

### Annotating Step 3

Ask yourself:
1. Does the comment actually target any of the load-bearing assumptions from Step 1? (Cross-check with your Step 1 reading, not the judge's Step 1)
2. Is the judge's assimilation / contrast / within-latitude classification correct?
   - **Assimilation check**: Does the comment genuinely add nothing new — just restate what the OP already believes?
   - **Contrast check**: Is the comment's position genuinely too far from the OP's for them to engage?
   - **Within-latitude check**: Does the comment make a targeted challenge the OP would have to actually address?
3. Does the judge's reasoning for its classification hold up?

**Rate 2** if the classification and its reasoning are correct.  
**Rate 1** if the classification is correct but the reasoning misidentifies which assumption is being targeted, or misapplies assimilation vs. contrast.  
**Rate 0** if the classification is wrong — e.g., the judge says "contrast" but the comment clearly engages a core concern the OP would consider.

> **Note:** Step 3 is where errors are most consequential. A misclassification here will cascade into a wrong final verdict regardless of how accurate Steps 1–2 were. Flag Step 3 errors prominently.

### Annotating Step 4

Ask yourself:
1. Does the comment actually acknowledge the OP's emotional register or concerns? Does the judge's assessment match?
2. Are the good-faith signals the judge mentions actually present in the comment text?
3. Is the credibility assessment grounded — does the judge identify real features of the comment (e.g., a concession, a cited fact, an admission of uncertainty)?

**Rate 2** if the assessment of tone and credibility signals matches what is in the comment.  
**Rate 1** if one element (e.g., tone vs. credibility) is assessed correctly but the other is off.  
**Rate 0** if the judge's assessment contradicts what the comment actually does (e.g., claims empathy when the comment is dismissive).

### Annotating Step 5

Ask yourself:
1. Does the verdict follow directly from what Step 3 found about the latitude of acceptance?
2. Does it correctly weight Step 4 — giving it secondary rather than primary influence?
3. Does it introduce any new reasoning not present in Steps 1–4, or contradict what the earlier steps established?

**Rate 2** if the verdict is a coherent, accurate synthesis of the prior steps — the reasoning explains the direction of the verdict and the prior steps support it.  
**Rate 1** if the verdict direction is right but the reasoning skips a step, over-weights a minor factor, or is vaguer than the chain warrants.  
**Rate 0** if the verdict contradicts the prior chain — e.g., Step 3 found the argument clearly within latitude but Step 5 concludes non-persuasive without new justification.

> **Note:** You are evaluating chain consistency, not whether you agree with the verdict. A Step 5 that coherently follows from a flawed Step 3 should be rated 2 for Step 5 — the error belongs to Step 3.

---

## Annotation Form

For each item, record the following:

```
Item:        [post_id]_[comment_id]   Model: [gpt5 / claude]

Step 1 — OP Belief State
  Rating:    [ 0 / 1 / 2 ]
  Notes:     ___________________________________________

Step 2 — Commenter Argument
  Rating:    [ 0 / 1 / 2 ]
  Notes:     ___________________________________________

Step 3 — Latitude of Acceptance        ← most important
  Rating:    [ 0 / 1 / 2 ]
  Classification used:  [ assimilation / contrast / within latitude ]
  Classification correct?  [ yes / no / partially ]
  Notes:     ___________________________________________

Step 4 — Credibility & Tone
  Rating:    [ 0 / 1 / 2 ]
  Notes:     ___________________________________________

Step 5 — Final Verdict (chain consistency only — no score)
  Rating:    [ 0 / 1 / 2 ]
  Follows from Step 3?      [ yes / no / partially ]
  Introduces new reasoning? [ yes / no ]
  Notes:     ___________________________________________
```

Notes are **required** when a rating is 0 or 1. One sentence is enough — identify what is wrong or missing.

---

## Common Errors to Watch For

| Error | What it looks like |
|---|---|
| **Invented assumption** | Step 1 lists a load-bearing assumption you cannot locate in the post text |
| **Paraphrase confusion** | Step 2 restates the comment accurately but mislabels it (e.g., calls speculation "evidence-based") |
| **Assimilation/contrast confusion** | Step 3 calls a targeted challenge "assimilation" because the commenter agrees on minor premises while disagreeing on the core claim |
| **Latitude too narrow** | Step 3 calls a moderate challenge "contrast" when it clearly engages the OP's position |
| **Tone projection** | Step 4 claims empathy or hostility not reflected in the comment's actual wording |
| **Compounding error** | Step 2 misreads the argument → Step 3 evaluates the wrong argument → verdict is wrong even though Step 3 reasoning is internally consistent |
| **Verdict reversal** | Step 5 contradicts the chain — e.g., Step 3 found the argument within latitude but Step 5 concludes non-persuasive without new justification |
| **Step 5 over-weights tone** | Step 5 lets a Step 4 finding (e.g., slightly poor tone) override a strong Step 3 finding, producing a lower verdict than the chain supports |

---

## Key Concepts

**Load-bearing assumption** (Step 1): The premise the OP's entire argument depends on. If you removed it, their position would collapse. Not every claim in the post is load-bearing — focus on the one or two that are structural.

**Latitude of acceptance** (Step 3): The range of positions the OP would genuinely consider. A persuasive comment does not need to be logically perfect — it needs to land in this zone. A comment that is technically correct but addresses the wrong assumption will not persuade, no matter how well-argued.

---

## Practice Test Case

Work through this item on your own before reading the expected annotations at the bottom.

---

### Item: `9vwr4u` / `e9fvl9v`

**Post title**

> CMV: Telling your kids to think about starving children so they would treasure their food doesn't make sense.

**Post text**

> When I was young, my mother would always tell me to cherish my food at the dinner table, and when I disliked it and stopped eating midway she would tell me to think of the poor children and families in Africa with nothing to dress and nothing to eat. Therefore, I shouldn't be wasting my food.
>
> While I can get behind the virtues of treasuring resources and not burdening the environment with leftovers that comes with eating the morsel in front of me, I couldn't quite wrap my head behind the notion that my actions would affect those who suffer from poorer conditions. For one if I ditch my food, I won't turn into a starving child, so I don't need to know about the ramifications of such. Also, even if I eat my food, I won't be helping them either, so what's the point of bringing them up?
>
> So the main reason for that is to elicit sympathy. But how does my sympathy relate to what I'm chided for? I sympathise with the starving children, so that's why I shouldn't waste my food? There seems to be a missing link here, something I still couldn't resolve after nearly a decade of pondering.

**Comment**

> Btw I get why you are confused here I think. Most of the time when we say "think of the X" it's because we're asking you to do something on their behalf. Think of the abandoned puppies; please adopt. Think of those who are starving; please donate to aid programs. End their suffering.
>
> Here this analogy asks you more to "think LIKE an X", not "think OF the X". An X out there wishes they could make this choice and wouldn't make a mistake with it, but can't because they don't have access to the same resources. So don't be stupid and make a bad choice with what resources you have.

---

**Step 1 — OP Belief State (as produced by the judge)**

> The OP believes the "think of starving kids" admonition is logically incoherent because their finishing (or not finishing) dinner neither harms nor helps starving children, so invoking them is just emotional guilt-tripping rather than a real moral reason. They're defending the position that waste-reduction should be justified by reasons like personal responsibility or environmental impact, not by an irrelevant comparison to distant suffering.
>
> Their load-bearing assumptions include: (1) a moral reprimand should track a direct or at least credible causal link between the act (wasting food) and the harm referenced (starvation elsewhere); (2) sympathy/empathy only "counts" as a reason to act when it translates into concrete help, not merely feeling bad; and (3) if an action doesn't change the outcome for the supposed victim, then referencing that victim is rhetorically manipulative rather than rationally justificatory.

**Step 2 — Commenter's Argument (as produced by the judge)**

> The commenter's core move is to reinterpret the phrase: it isn't claiming your uneaten food will affect starving children, but urging you to "think like" someone who lives with scarcity and would treat that food as precious. On this reading, the point is prudence and humility — don't squander a valuable option that others would desperately want — rather than direct moral causation or charity.
>
> Epistemically, they're arguing from a social-norms/educational perspective: common phrases are shorthand, and the intended lesson is about cultivating a mindset toward resources, not establishing a literal cause-effect link. They believe the OP's confusion comes from taking the phrase as "do something for them," whereas it's meant as "adopt the perspective of scarcity to guide your own choices."

**Step 3 — Latitude of Acceptance (as produced by the judge)**

> The OP's latitude of acceptance likely includes explanations that preserve their demand for non-magical causality (i.e., not claiming their leftovers feed anyone), but that supply a coherent normative link — e.g., "this is about cultivating gratitude, anti-waste habits, or a scarcity mindset," rather than direct harm/benefit to Africa. They seem open to virtue-ethics or character-formation rationales as long as the reasoning is explicit and not just guilt by association.
>
> The commenter's "think LIKE, not think OF" reframing lands within that latitude: it directly addresses the OP's missing-link complaint and avoids asserting a false causal connection. It's also discrepant enough to potentially move the OP (it changes what the phrase is *doing*), without being so moralizing or abstract that it triggers rejection.
>
> So it neither contrasts nor merely assimilates; it offers a meaningfully different interpretation that the OP can accept without abandoning their core logic-first stance.

**Step 4 — Credibility and Tone (as produced by the judge)**

> The commenter partially matches the OP's register by opening with "I get why you are confused," which acknowledges the OP's puzzlement and implies the concern is reasonable. They mostly signal good faith by treating the issue as a linguistic/interpretive mismatch rather than a moral failure, and by implicitly sharing the value of reducing waste. However, the line "So don't be stupid" risks breaking that rapport by sounding dismissive, which could undercut perceived respect and credibility even if the underlying point is charitable. They do manage credibility somewhat by conceding the OP's strongest point (that "think of X" usually implies helping X) before offering the alternative "think like X" interpretation.

**Step 5 — Final Verdict (as produced by the judge)**

> The comment directly targets the OP's load-bearing assumption that the admonition must imply a causal link to starving children, offering a coherent "think like someone in scarcity" reframing that fits the OP's logic-first stance and sits within their latitude of acceptance. It also concedes the OP's strongest interpretive point upfront, but slightly undermines rapport with the "don't be stupid" phrasing, which could trigger defensiveness.

---

### Expected Annotations

**Step 1 — Rating: 2 (Correct)**

The judge correctly identifies the OP's core claim (the admonition is logically incoherent) and all three load-bearing assumptions are grounded in specific sentences in the post. No invented content. You could locate each assumption in the post text if asked.

**Step 2 — Rating: 2 (Correct)**

The "think LIKE vs think OF" reinterpretation is exactly what the comment does. The epistemic stance (treating the phrase as social shorthand for a mindset, not a causal claim) is accurate and not over-interpreted. The judge does not add intent the comment didn't express.

**Step 3 — Rating: 2 (Correct)**

This is the most important step to get right. The OP's core complaint is the *missing causal link* — they can't see how their eating affects anyone else. The commenter addresses this directly by offering a reading that requires no causal link at all (it's about adopting a mindset). The judge correctly classifies this as *within latitude* rather than assimilation or contrast, and the explanation holds up: the OP's logic-first stance is preserved while the normative ground shifts. The judge also correctly notes it is "discrepant enough to move" — it doesn't just agree, it reframes the premise.

> **Watch point:** A common error here would be to classify this as *assimilation* because the comment opens with "I get why you are confused" (empathy) or doesn't directly attack the OP's position. That would be wrong — empathetic framing at the start doesn't neutralise the core reframe in the body of the comment.

**Step 4 — Rating: 2 (Correct)**

The judge correctly notices that the opening ("I get why you are confused") signals genuine engagement, and correctly flags "don't be stupid" as a credibility risk. Both observations are grounded in specific phrases in the comment. This is an example of a step-4 judgment that is neither generous nor uncharitable — it accurately captures the mixed quality of the commenter's tone management.

> **Watch point:** Do not rate Step 4 based on whether *you* find the comment condescending. Rate it based on whether the *judge's characterisation* of the comment's tone and credibility signals matches the text.

**Step 5 — Rating: 2 (Correct)**

Step 5 draws directly on the Step 3 finding ("sits within their latitude of acceptance") as the primary driver of the verdict, and folds in the Step 4 credibility risk ("don't be stupid" undermining rapport) as a secondary qualifier. It introduces no new claims and does not reverse direction. The verdict is a faithful compression of the chain.

> **Watch point:** Step 5 should be rated on consistency with the chain, not on whether you agree with the verdict. If Steps 1–4 were all rated 2 and Step 5 follows from them, Step 5 is also 2 — even if you personally think the comment isn't that persuasive.

---

