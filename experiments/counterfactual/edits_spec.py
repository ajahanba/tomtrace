"""
Hand-drafted Step-3 edits (Phase 2). Each entry is a list of exact
(original sentence, replacement sentence) pairs applied to the raw Step-3 text
in PaTom/results/sample_outputs/chain_fullrubric_claude_1000.jsonl.
Only sentences that state or hedge the latitude classification are replaced;
all other text stays byte-identical.

Conditions:
  to_within   : TARGET items, commit to "within latitude"
  to_contrast : REVERSE items, commit to "contrast" (OP likely rejects as too far)
  paraphrase  : every TARGET and REVERSE item, reword without changing the call
"""

EDITS = {
    # ------------------------------------------------------------------ TARGETS
    "1otj7pk|no4x7oe|claude": {
        "to_within": [
            ('''The comment partially lands within her latitude of acceptance but fails to travel far enough to produce meaningful view change.''',
             '''The comment lands within her latitude of acceptance and travels far enough to give her a reason to reconsider.'''),
            ('''This argument largely **assimilates** — the OP would likely read it as basic agreement dressed in slightly different language ("yes, it's wrong, but people are dumb"), which she already implicitly acknowledges.''',
             '''This argument falls **within her latitude of acceptance** rather than assimilating — the OP would likely not read it as mere agreement dressed in slightly different language ("yes, it's wrong, but people are dumb").'''),
        ],
        "paraphrase": [
            ('''The comment partially lands within her latitude of acceptance but fails to travel far enough to produce meaningful view change.''',
             '''The comment only partly falls inside her latitude of acceptance and does not go far enough to bring about meaningful view change.'''),
            ('''This argument largely **assimilates** — the OP would likely read it as basic agreement dressed in slightly different language ("yes, it's wrong, but people are dumb"), which she already implicitly acknowledges.''',
             '''For the most part this argument **assimilates** — the OP would probably take it as basic agreement in slightly different words ("yes, it's wrong, but people are dumb"), something she already implicitly acknowledges.'''),
        ],
    },
    "12a4eco|jeqh3bc|claude": {
        "to_within": [
            ('''The argument risks **assimilation** more than contrast — the OP may simply agree that TST is reasonable while arguing it doesn't qualify as a "religion" in the sense they meant, or that TST makes no supernatural claims and therefore isn't the kind of religion their view was targeting.''',
             '''The argument lands **within latitude** rather than assimilating or contrasting — the OP cannot simply agree that TST is reasonable while arguing it doesn't qualify as a "religion" in the sense they meant, or that TST makes no supernatural claims and therefore isn't the kind of religion their view was targeting.'''),
            ('''Rather than moving the OP's position, it may be absorbed as a friendly footnote that doesn't actually challenge the load-bearing assumptions about supernatural religious claims requiring extraordinary evidence.''',
             '''Rather than being absorbed as a friendly footnote, it is positioned to move the OP's position on the load-bearing assumptions about supernatural religious claims requiring extraordinary evidence.'''),
        ],
        "paraphrase": [
            ('''The argument risks **assimilation** more than contrast — the OP may simply agree that TST is reasonable while arguing it doesn't qualify as a "religion" in the sense they meant, or that TST makes no supernatural claims and therefore isn't the kind of religion their view was targeting.''',
             '''Assimilation is a greater risk for this argument than contrast — the OP may just agree that TST is reasonable while maintaining it isn't a "religion" in the sense they intended, or that because TST makes no supernatural claims it isn't the kind of religion their view targeted.'''),
            ('''Rather than moving the OP's position, it may be absorbed as a friendly footnote that doesn't actually challenge the load-bearing assumptions about supernatural religious claims requiring extraordinary evidence.''',
             '''Instead of shifting the OP's position, it may be taken in as a friendly footnote that leaves the load-bearing assumptions about supernatural religious claims requiring extraordinary evidence untouched.'''),
        ],
    },
    "t1e0go|hygrp3z|claude": {
        "to_within": [
            ('''However, the commenter's conclusion — that artists are *justified* in being upset at the comparison itself, not just its misuse — directly attacks the OP's core anchor rather than approaching it obliquely, which risks triggering contrast rather than acceptance.''',
             '''However, the commenter's conclusion — that artists are *justified* in being upset at the comparison itself, not just its misuse — directly attacks the OP's core anchor rather than approaching it obliquely, but stays close enough to the OP's own distinction to be considered rather than rejected.'''),
            ('''The argument sits at the edge of the latitude — neither pure assimilation nor full contrast.''',
             '''The argument lands within the latitude — it is neither assimilation nor contrast.'''),
        ],
        "paraphrase": [
            ('''However, the commenter's conclusion — that artists are *justified* in being upset at the comparison itself, not just its misuse — directly attacks the OP's core anchor rather than approaching it obliquely, which risks triggering contrast rather than acceptance.''',
             '''However, the commenter's conclusion — that artists are *justified* in being upset at the comparison itself, not just its misuse — directly attacks the OP's core anchor rather than approaching it obliquely, so it could provoke contrast instead of acceptance.'''),
            ('''The argument sits at the edge of the latitude — neither pure assimilation nor full contrast.''',
             '''The argument is positioned on the boundary of the latitude — not purely assimilation, nor fully contrast.'''),
        ],
    },
    "kq762d|gi29gkn|claude": {
        "to_within": [
            ('''The commenter's argument lands *mostly within* the OP's latitude of acceptance, but with uneven force.''',
             '''The commenter's argument lands *within* the OP's latitude of acceptance.'''),
            ('''The hateful-comments-attract-replies point risks mild *contrast* — the OP's concern is specifically about downvoting replacing argumentation in good-faith discussions, so invoking hate speech may feel like a strawman of their position.''',
             '''The hateful-comments-attract-replies point does not tip into *contrast*, even though the OP's concern is specifically about downvoting replacing argumentation in good-faith discussions and invoking hate speech may feel like a strawman of their position.'''),
            ('''The "insightful comments get few replies" point risks *assimilation* — the OP might already agree this is a problem but see it as a separate issue from voting mechanics.''',
             '''The "insightful comments get few replies" point does not collapse into *assimilation*, even though the OP might already agree this is a problem.'''),
            ('''Overall, the argument is calibrated well enough to avoid outright rejection but is not uniformly persuasive across all its sub-claims.''',
             '''Overall, the argument is calibrated to land within the OP's latitude of acceptance across its sub-claims.'''),
        ],
        "paraphrase": [
            ('''The commenter's argument lands *mostly within* the OP's latitude of acceptance, but with uneven force.''',
             '''The commenter's argument falls *largely inside* the OP's latitude of acceptance, though its force is uneven.'''),
            ('''The hateful-comments-attract-replies point risks mild *contrast* — the OP's concern is specifically about downvoting replacing argumentation in good-faith discussions, so invoking hate speech may feel like a strawman of their position.''',
             '''The hateful-comments-attract-replies point carries a mild risk of *contrast* — since the OP's concern is specifically about downvoting replacing argumentation in good-faith discussions, bringing in hate speech may read as a strawman of their position.'''),
            ('''The "insightful comments get few replies" point risks *assimilation* — the OP might already agree this is a problem but see it as a separate issue from voting mechanics.''',
             '''The "insightful comments get few replies" point carries a risk of *assimilation* — the OP may already agree it is a problem yet treat it as separate from voting mechanics.'''),
            ('''Overall, the argument is calibrated well enough to avoid outright rejection but is not uniformly persuasive across all its sub-claims.''',
             '''Overall, the argument is calibrated enough to escape outright rejection, but its sub-claims are not equally persuasive.'''),
        ],
    },
    "1ewdslq|liycs35|claude": {
        "to_within": [
            ('''The commenter's argument lands *outside* the OP's latitude of acceptance, but not because it's too radical — rather, it fails to engage the OP's actual grievance and implicitly minimizes it through comparison.''',
             '''The commenter's argument lands *within* the OP's latitude of acceptance, even though it does not fully engage the OP's actual grievance and implicitly minimizes it through comparison.'''),
            ('''This argument is likely to trigger **contrast** — the OP will probably read it as a motorcycle apologist using a whataboutism deflection (dogs are worse!) rather than a genuine engagement with the enforcement failure and deliberate inconsiderateness they find most enraging, causing them to dig in rather than shift.''',
             '''This argument is likely to land **within latitude** rather than trigger contrast — the OP will probably not read it as a motorcycle apologist using a whataboutism deflection (dogs are worse!), but as engaging the problem they find most enraging, so they may shift rather than dig in.'''),
        ],
        "paraphrase": [
            ('''The commenter's argument lands *outside* the OP's latitude of acceptance, but not because it's too radical — rather, it fails to engage the OP's actual grievance and implicitly minimizes it through comparison.''',
             '''The commenter's argument falls *outside* the OP's latitude of acceptance, not for being too radical but because it does not engage the OP's actual grievance and implicitly downplays it by comparison.'''),
            ('''This argument is likely to trigger **contrast** — the OP will probably read it as a motorcycle apologist using a whataboutism deflection (dogs are worse!) rather than a genuine engagement with the enforcement failure and deliberate inconsiderateness they find most enraging, causing them to dig in rather than shift.''',
             '''This argument will probably provoke **contrast** — the OP is likely to see it as a motorcycle apologist's whataboutism (dogs are worse!) rather than real engagement with the enforcement failure and deliberate inconsiderateness that enrage them most, so they dig in instead of shifting.'''),
        ],
    },
    "ubwcpp|i67n15h|claude": {
        "to_within": [
            ('''No — the commenter's response does not land within the OP's latitude of acceptance in any persuasively useful way.''',
             '''Yes — the commenter's response lands within the OP's latitude of acceptance in a persuasively useful way.'''),
            ('''The comment assimilates entirely — it essentially restates and reinforces what the OP already believes.''',
             '''The comment lands within latitude rather than assimilating — it does more than restate and reinforce what the OP already believes.'''),
            ('''From the OP's perspective, this comment reads as validation, not challenge, making it persuasively inert.''',
             '''From the OP's perspective, this comment reads as a challenge, not mere validation, which gives it persuasive force.'''),
        ],
        "paraphrase": [
            ('''No — the commenter's response does not land within the OP's latitude of acceptance in any persuasively useful way.''',
             '''No — in no persuasively useful sense does the commenter's response fall within the OP's latitude of acceptance.'''),
            ('''The comment assimilates entirely — it essentially restates and reinforces what the OP already believes.''',
             '''The comment is a case of complete assimilation — it basically restates and reinforces what the OP already believes.'''),
            ('''From the OP's perspective, this comment reads as validation, not challenge, making it persuasively inert.''',
             '''To the OP, this comment reads as validation rather than challenge, which leaves it persuasively inert.'''),
        ],
    },
    "8skv52|e10o3x9|claude": {
        "to_within": [
            ('''The argument risks **assimilation** more than contrast — the OP has *already* conceded voting in their edit, so the commenter is largely confirming a position the OP reached independently rather than pushing them somewhere new.''',
             '''The argument lands **within latitude** rather than assimilating — although the OP has *already* conceded voting in their edit, the commenter is pushing them beyond the position the OP reached independently.'''),
        ],
        "paraphrase": [
            ('''The argument risks **assimilation** more than contrast — the OP has *already* conceded voting in their edit, so the commenter is largely confirming a position the OP reached independently rather than pushing them somewhere new.''',
             '''Assimilation is a greater risk for this argument than contrast — the OP has *already* conceded voting in their edit, so the commenter mostly confirms a position the OP arrived at independently instead of moving them somewhere new.'''),
        ],
    },
    # ------------------------------------------------------------------ REVERSE
    "1dlyt3u|l9shm76|claude": {
        "to_contrast": [
            ('''Yes, and strategically so.''', '''No — it lands outside it.'''),
            ('''Neither — this argument is well-calibrated to produce genuine movement.''',
             '''Contrast — this argument is likely to be rejected as too far from the OP's position.'''),
            ('''It is discrepant enough from the OP's anchor to require real reconsideration (it inverts their hand-holding premise rather than merely qualifying it), but it does so using the OP's own values as leverage, preventing the kind of ideological rejection that would trigger contrast effects.''',
             '''It is too discrepant from the OP's anchor to be considered (it inverts their hand-holding premise rather than merely qualifying it), and using the OP's own values as leverage does not prevent the kind of ideological rejection that triggers contrast effects.'''),
        ],
        "paraphrase": [
            ('''Yes, and strategically so.''', '''It does, and in a strategic way.'''),
            ('''Neither — this argument is well-calibrated to produce genuine movement.''',
             '''Neither applies — the argument is calibrated well enough to produce real movement.'''),
            ('''It is discrepant enough from the OP's anchor to require real reconsideration (it inverts their hand-holding premise rather than merely qualifying it), but it does so using the OP's own values as leverage, preventing the kind of ideological rejection that would trigger contrast effects.''',
             '''It departs far enough from the OP's anchor to demand real reconsideration (inverting rather than merely qualifying their hand-holding premise), yet it leans on the OP's own values, which heads off the ideological rejection that produces contrast effects.'''),
        ],
    },
    "2p6y53|cmu3xmz|claude": {
        "to_contrast": [
            ('''Yes — the commenter's argument lands squarely within the OP's latitude of acceptance, and does so with precision.''',
             '''No — the commenter's argument lands outside the OP's latitude of acceptance, too far from their position to be considered.'''),
            ('''The commenter explicitly concedes the OP's point about harmful cosmetic breeding (toy breeds, exaggerated conformation), which prevents contrast-rejection by signaling shared values.''',
             '''The commenter explicitly concedes the OP's point about harmful cosmetic breeding (toy breeds, exaggerated conformation), but signaling shared values this way does not prevent contrast-rejection.'''),
            ('''Neither — this argument is well-calibrated.''',
             '''Contrast — the OP is likely to reject this argument as too far from their position.'''),
            ('''It avoids assimilation by introducing genuinely new empirical content (innate instincts as breed-specific, not trainable), and avoids contrast by conceding the OP's strongest points upfront, making the disagreement feel like a targeted refinement rather than a wholesale rejection of their worldview.''',
             '''It avoids assimilation by introducing genuinely new empirical content (innate instincts as breed-specific, not trainable), but conceding the OP's strongest points upfront does not avoid contrast: the disagreement is likely to feel like a wholesale rejection of their worldview rather than a targeted refinement.'''),
        ],
        "paraphrase": [
            ('''Yes — the commenter's argument lands squarely within the OP's latitude of acceptance, and does so with precision.''',
             '''Yes — the commenter's argument falls squarely inside the OP's latitude of acceptance, and precisely so.'''),
            ('''The commenter explicitly concedes the OP's point about harmful cosmetic breeding (toy breeds, exaggerated conformation), which prevents contrast-rejection by signaling shared values.''',
             '''The commenter explicitly concedes the OP's point about harmful cosmetic breeding (toy breeds, exaggerated conformation), which, by signaling shared values, heads off contrast-rejection.'''),
            ('''Neither — this argument is well-calibrated.''', '''Neither — the argument is well calibrated.'''),
            ('''It avoids assimilation by introducing genuinely new empirical content (innate instincts as breed-specific, not trainable), and avoids contrast by conceding the OP's strongest points upfront, making the disagreement feel like a targeted refinement rather than a wholesale rejection of their worldview.''',
             '''Introducing genuinely new empirical content (innate instincts as breed-specific, not trainable) keeps it from assimilating, and conceding the OP's strongest points upfront keeps it from contrasting, so the disagreement reads as a targeted refinement rather than a wholesale rejection of their worldview.'''),
        ],
    },
    "altl91|efjefbu|claude": {
        "to_contrast": [
            ('''Yes, and quite precisely so.''', '''No — it lands outside it.'''),
            ('''This is far enough from the OP's anchor to prompt genuine reconsideration, but not so discrepant as to trigger rejection.''',
             '''This is so discrepant from the OP's anchor that it is likely to trigger rejection rather than genuine reconsideration.'''),
            ('''Neither risk is significant here.''', '''Contrast is the significant risk here.'''),
            ('''The commenter avoids assimilation by not simply agreeing that HETs are bad, and avoids contrast by not making sweeping environmental claims the OP would dismiss.''',
             '''The commenter avoids assimilation by not simply agreeing that HETs are bad, but the OP is likely to dismiss the argument as too far from their position.'''),
            ('''The argument occupies the productive middle ground — empirically grounded, experientially relatable, and practically actionable — which is precisely where persuasion becomes possible for this particular OP.''',
             '''The argument falls outside the productive middle ground — whatever its empirical grounding, relatability, and practicality — in the zone this particular OP would reject.'''),
        ],
        "paraphrase": [
            ('''Yes, and quite precisely so.''', '''It does, and with considerable precision.'''),
            ('''This is far enough from the OP's anchor to prompt genuine reconsideration, but not so discrepant as to trigger rejection.''',
             '''This sits far enough from the OP's anchor to prompt real reconsideration without being so discrepant that it triggers rejection.'''),
            ('''Neither risk is significant here.''', '''Neither risk matters much here.'''),
            ('''The commenter avoids assimilation by not simply agreeing that HETs are bad, and avoids contrast by not making sweeping environmental claims the OP would dismiss.''',
             '''By not simply agreeing that HETs are bad the commenter avoids assimilation, and by not making sweeping environmental claims the OP would dismiss it avoids contrast.'''),
            ('''The argument occupies the productive middle ground — empirically grounded, experientially relatable, and practically actionable — which is precisely where persuasion becomes possible for this particular OP.''',
             '''The argument sits in the productive middle ground — empirically grounded, experientially relatable, and practically actionable — exactly where persuasion becomes possible for this particular OP.'''),
        ],
    },
    "5q3wh6|dcw4qag|claude": {
        "to_contrast": [
            ('''Yes — and quite precisely.''', '''No — it lands outside it.'''),
            ('''This is close enough to the OP's existing pragmatic framework to be credible and non-threatening, yet genuinely new information that reframes the entire premise.''',
             '''This is too far from the OP's existing pragmatic framework to be credible and non-threatening, even though it is genuinely new information that reframes the entire premise.'''),
            ('''Neither extreme applies here.''', '''Contrast applies here.'''),
            ('''The argument doesn't merely restate the OP's position, nor does it leap to an incompatible worldview.''',
             '''The argument doesn't merely restate the OP's position, but it leaps to a worldview the OP is likely to reject as incompatible.'''),
            ('''It meets the OP on their own pragmatic, security-focused terrain while introducing a factual correction that directly undermines their core assumption — the ideal persuasive distance for this particular OP.''',
             '''It approaches the OP's pragmatic, security-focused terrain while introducing a factual correction that directly undermines their core assumption — too far for this particular OP to consider.'''),
        ],
        "paraphrase": [
            ('''Yes — and quite precisely.''', '''It does — and with precision.'''),
            ('''This is close enough to the OP's existing pragmatic framework to be credible and non-threatening, yet genuinely new information that reframes the entire premise.''',
             '''It sits close enough to the OP's existing pragmatic framework to seem credible and non-threatening, while still being genuinely new information that reframes the whole premise.'''),
            ('''Neither extreme applies here.''', '''Neither extreme is relevant here.'''),
            ('''The argument doesn't merely restate the OP's position, nor does it leap to an incompatible worldview.''',
             '''The argument neither just restates the OP's position nor jumps to an incompatible worldview.'''),
            ('''It meets the OP on their own pragmatic, security-focused terrain while introducing a factual correction that directly undermines their core assumption — the ideal persuasive distance for this particular OP.''',
             '''It engages the OP on their own pragmatic, security-focused ground while introducing a factual correction that directly undermines their core assumption — the ideal persuasive distance for this particular OP.'''),
        ],
    },
    "1mdcvh|cc84ghp|claude": {
        "to_contrast": [
            ('''Yes, largely.''', '''No, largely not.'''),
            ('''The commenter makes the strategically sound move of *not* disputing the OP's core scientific claims about prion resilience, which avoids triggering the contrast effect.''',
             '''The commenter makes the move of *not* disputing the OP's core scientific claims about prion resilience, but this does not avoid triggering the contrast effect.'''),
            ('''There is a mild contrast risk around the milk concern, which the commenter doesn't directly address — leaving the OP's most personally salient fear partially unresolved, which could limit full persuasion.''',
             '''Contrast is the likely outcome: the commenter doesn't directly address the milk concern, leaving the OP's most personally salient fear unresolved, so the OP is likely to reject the argument as too far from their position.'''),
        ],
        "paraphrase": [
            ('''Yes, largely.''', '''For the most part, yes.'''),
            ('''The commenter makes the strategically sound move of *not* disputing the OP's core scientific claims about prion resilience, which avoids triggering the contrast effect.''',
             '''By *not* disputing the OP's core scientific claims about prion resilience, the commenter makes a strategically sound move that keeps the contrast effect from being triggered.'''),
            ('''There is a mild contrast risk around the milk concern, which the commenter doesn't directly address — leaving the OP's most personally salient fear partially unresolved, which could limit full persuasion.''',
             '''A mild contrast risk exists around the milk concern, which the commenter leaves unaddressed — the OP's most personally salient fear stays partly unresolved, which may limit full persuasion.'''),
        ],
    },
    "1o8oslz|njzw2ah|claude": {
        "to_contrast": [
            ('''Yes, largely.''', '''No, largely not.'''),
            ('''This is precisely the kind of targeted, constructive refinement the OP invited, making it highly likely to fall within their acceptance range rather than triggering reactance.''',
             '''Although this is the kind of targeted, constructive refinement the OP invited, it is likely to fall outside their acceptance range and trigger reactance.'''),
            ('''The argument neither fully assimilates nor contrasts — it occupies a productive middle zone.''',
             '''The argument contrasts — the OP is likely to reject it as too far from their position.'''),
            ('''The disability critique is a genuine challenge to one of the OP's stated criteria, while the alternative proposals (vet-visit licensing, owner licensing) are close enough to the OP's framework to feel like evolution rather than rejection, minimizing the risk of contrast-effect dismissal.''',
             '''The disability critique is a genuine challenge to one of the OP's stated criteria, and the alternative proposals (vet-visit licensing, owner licensing) are far enough from the OP's framework to feel like rejection rather than evolution, inviting contrast-effect dismissal.'''),
        ],
        "paraphrase": [
            ('''Yes, largely.''', '''For the most part, yes.'''),
            ('''This is precisely the kind of targeted, constructive refinement the OP invited, making it highly likely to fall within their acceptance range rather than triggering reactance.''',
             '''It is exactly the targeted, constructive refinement the OP asked for, so it will very likely fall inside their acceptance range instead of triggering reactance.'''),
            ('''The argument neither fully assimilates nor contrasts — it occupies a productive middle zone.''',
             '''The argument does not fully assimilate or contrast — it sits in a productive middle zone.'''),
            ('''The disability critique is a genuine challenge to one of the OP's stated criteria, while the alternative proposals (vet-visit licensing, owner licensing) are close enough to the OP's framework to feel like evolution rather than rejection, minimizing the risk of contrast-effect dismissal.''',
             '''The disability critique genuinely challenges one of the OP's stated criteria, and the alternative proposals (vet-visit licensing, owner licensing) sit close enough to the OP's framework to read as evolution rather than rejection, keeping the risk of contrast-effect dismissal low.'''),
        ],
    },
    "3izepf|cul8cco|claude": {
        "to_contrast": [
            ('''The commenter's argument lands squarely within the OP's latitude of acceptance because it explicitly adopts the OP's own efficiency framework and turns it against their conclusion.''',
             '''The commenter's argument lands outside the OP's latitude of acceptance even though it explicitly adopts the OP's own efficiency framework and turns it against their conclusion.'''),
            ('''This is precisely the kind of systemic, instrumentalist counter-argument the OP's reasoning style would find credible rather than dismissive.''',
             '''Even so, the OP's reasoning style is likely to find this systemic, instrumentalist counter-argument too far from their position to be credible.'''),
            ('''There is minimal contrast risk here, and the argument avoids assimilation by introducing genuinely new information (the WWF flagship/footprint distinction) that the OP likely hadn't factored into their reasoning.''',
             '''Contrast is the main risk here, even though the argument avoids assimilation by introducing genuinely new information (the WWF flagship/footprint distinction) that the OP likely hadn't factored into their reasoning.'''),
        ],
        "paraphrase": [
            ('''The commenter's argument lands squarely within the OP's latitude of acceptance because it explicitly adopts the OP's own efficiency framework and turns it against their conclusion.''',
             '''Because it explicitly adopts the OP's own efficiency framework and turns it against their conclusion, the commenter's argument falls squarely inside the OP's latitude of acceptance.'''),
            ('''This is precisely the kind of systemic, instrumentalist counter-argument the OP's reasoning style would find credible rather than dismissive.''',
             '''The OP's reasoning style would find exactly this kind of systemic, instrumentalist counter-argument credible rather than dismissive.'''),
            ('''There is minimal contrast risk here, and the argument avoids assimilation by introducing genuinely new information (the WWF flagship/footprint distinction) that the OP likely hadn't factored into their reasoning.''',
             '''Contrast risk is minimal here, and by introducing genuinely new information (the WWF flagship/footprint distinction) the OP likely hadn't factored in, the argument avoids assimilation.'''),
        ],
    },
}
