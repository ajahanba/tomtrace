#!/usr/bin/env python3
"""
Cut and validity rules for regenerated Step 4 outputs (follow-up run).
Rules were fixed and recorded in README.md before any follow-up call was rerun.

cut(text)       -> (kept_text, cut_reason)
    Keeps the text before "END OF STEP 4" or before the first echoed turn marker,
    whichever comes first. A leading echo ending in "[ASSISTANT - Step 4]" within
    the first 200 characters is dropped. Nothing else is changed.
check(text)     -> list of failure reasons (empty = valid)
    length outside 600-2,500 characters; a turn label ("[USER", "[ASSISTANT", "[STEP"
    or any mention of Step 5); "Score:" or a numeric 1-10 rating; verdict language
    (earn/award/win/receive/get a delta, final score/verdict/rating, delta-worthy);
    a meta-response (opening "Understood", "Okay", "Sure", "Noted", "Note that this
    step", ..., or "I will hold" anywhere).
"""

import re

END = "END OF STEP 4"
MARKER = re.compile(r"\[(?:USER|ASSISTANT)\s*-\s*Step\s*\d\]", re.I)
LEAD_ECHO = re.compile(r"(?s)^.{0,200}?\[ASSISTANT\s*-\s*Step\s*4\]\s*", re.I)
MIN_LEN, MAX_LEN = 600, 2500

TURN_LABEL = re.compile(r"\[(?:USER|ASSISTANT|STEP)\b|\bStep\s*5\b", re.I)   # back-references to Steps 1-3 are allowed
SCORE = re.compile(r"(?i)\bscore\s*:|\b(?:[1-9]|10)\s*(?:/|out of)\s*10\b|"
                   r"\b(?:score|rating|rate[sd]?|earns?|earned|merits?|deserves?)\s+(?:of\s+|a\s+|an\s+|it\s+)?"
                   r"\**\s*(?:[1-9]|10)\b(?!\s*(?:%|percent|years?|people|points of))")
VERDICT = re.compile(r"(?i)\b(?:earn(?:s|ed|ing)?|award(?:s|ed|ing)?|win(?:s|ning)?|receive[sd]?|get(?:s|ting)?)\s+"
                     r"(?:a|the)\s+delta\b|\bfinal\s+(?:score|verdict|rating)\b|\bdelta[- ]worthy\b")
META = re.compile(r"(?i)^\W*(?:understood|okay|ok\b|sure\b|got it|noted|certainly|i will hold|i'll hold|"
                  r"note that this step|i'll wait|i will wait|waiting for)|\bI(?: will|'ll) hold\b")


def cut(text):
    t = text
    m = LEAD_ECHO.match(t)
    if m:
        t = t[m.end():]
    cands = []
    i = t.find(END)
    if i >= 0:
        cands.append((i, "END OF STEP 4"))
    mm = MARKER.search(t)
    if mm:
        cands.append((mm.start(), "turn marker " + mm.group()))
    if not cands:
        return t.strip(), "none"
    pos, why = min(cands)
    return t[:pos].strip(), why


def check(text):
    fails = []
    if not MIN_LEN <= len(text) <= MAX_LEN:
        fails.append(f"length {len(text)}")
    for name, rx in (("turn label", TURN_LABEL), ("score/rating", SCORE), ("verdict language", VERDICT),
                     ("meta-response", META)):
        m = rx.search(text)
        if m:
            fails.append(f"{name}: {m.group().strip()!r}")
    return fails
