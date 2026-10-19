#!/usr/bin/env python3
"""
Rebuild the exact PAToM multi-turn message list for a Claude Sonnet 4.6 chain,
up to (and including) the Step-5 user turn, optionally replacing Step 3.

Sources (read-only):
  prompts / builders : PaTom/chain_of_tom/chain_of_tom.py (system prompt, step turns)
  ToM profiles       : PaTom/data/benchmark/cmv_tom_pairs_1000.json (Qwen3-30B-A3B extraction)
  assistant turns    : PaTom/results/sample_outputs/chain_fullrubric_claude_1000.jsonl
                       (exact model outputs; data/tomtrace.jsonl has whitespace collapsed)
  post / comment text: MSO222_PersuasionReasoningAnnotation_50.json (same text that
                       code/rehydrate.py recovers from Arctic Shift)

Usage:
  python3 reconstruct.py                 # writes reconstruction_check.md for 2 chains
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))       # project folder
PATOM = os.path.join(ROOT, "PaTom")
sys.path[:0] = [os.path.join(PATOM, "llm_judge"), os.path.join(PATOM, "chain_of_tom")]

from data_loader import Comment, Sample, _build_tom_from_pair_fields  # noqa: E402
import chain_of_tom as C                                             # noqa: E402

RELEASE = os.path.abspath(os.path.join(HERE, "..", ".."))
MODEL_ID = "claude-sonnet-4-6"
TEMPERATURE = 0.2          # PaTom/llm_judge/judge.py JudgeConfig default
MAX_TOKENS = 768           # per turn, same source


def _load():
    pairs = {(p["post_id"], p["comment_id"]): p for p in
             json.load(open(os.path.join(PATOM, "data", "benchmark", "cmv_tom_pairs_1000.json")))["pairs"]}
    chains = {(r["post_id"], r["comment_id"]): r for r in
              map(json.loads, open(os.path.join(PATOM, "results", "sample_outputs",
                                                "chain_fullrubric_claude_1000.jsonl")))}
    texts = {(x["post_id"], x["comment_id"]): x for x in
             json.load(open(os.path.join(ROOT, "MSO222_PersuasionReasoningAnnotation_50.json")))}
    return pairs, chains, texts


PAIRS, CHAINS, TEXTS = _load()


def build_messages(post_id, comment_id, step3_text=None, step4_text=None):
    """Messages [system, user1, asst1, user2, asst2, user3, asst3, user4, asst4, user5]."""
    k = (post_id, comment_id)
    pr, ch, tx = PAIRS[k], CHAINS[k], TEXTS[k]
    sample = Sample(post_id=post_id, post_title=tx["Post title"], post_body=tx["Post text"],
                    post_tom=_build_tom_from_pair_fields(pr["post_values"], pr["post_content"]))
    com = Comment(id=comment_id, body=tx["Comment text"], comment_type="persuasive",
                  tom=_build_tom_from_pair_fields(pr["comment_values"], pr["comment_content"]))
    m = C.init_chain_step1(sample)
    m = C.extend_step2(m, ch["step1_output"], com)
    m = C.extend_step3(m, ch["step2_output"], com)
    m = C.extend_step4(m, ch["step3_output"] if step3_text is None else step3_text, sample, com)
    m = C.extend_step5(m, ch["step4_output"] if step4_text is None else step4_text)
    return m


def original(post_id, comment_id):
    return CHAINS[(post_id, comment_id)]


def parse_score(text):
    """Same parser as PaTom/chain_of_tom/chain_of_tom.py run_chain_of_tom."""
    import re
    matches = re.findall(r"(?:Score|SCORE)[:]\s*\*{0,2}\s*(\d{1,2})", text)
    if not matches:
        return None
    val = int(matches[-1])
    return val if 1 <= val <= 10 else None


def main():
    rel = [json.loads(l) for l in open(os.path.join(RELEASE, "data", "tomtrace.jsonl"))]
    claude = [r for r in rel if r["judge"] == "claude"][:2]
    out = ["# Reconstruction check (no API calls)\n",
           f"Model: `{MODEL_ID}`, temperature {TEMPERATURE}, max_tokens {MAX_TOKENS} per turn.\n"]
    for r in claude:
        msgs = build_messages(r["post_id"], r["comment_id"])
        ch = original(r["post_id"], r["comment_id"])
        out.append(f"\n## {r['item_id']}  (original score {ch['generated_score']}; "
                   f"parser on stored Step 5 -> {parse_score(ch['raw_response'])})\n")
        for i, m in enumerate(msgs):
            out.append(f"\n### [{i}] {m['role'].upper()}\n\n```\n{m['content']}\n```\n")
        out.append(f"\n### [stored Step 5 output, for comparison]\n\n```\n{ch['raw_response']}\n```\n")
    path = os.path.join(HERE, "reconstruction_check.md")
    open(path, "w").write("".join(out))
    for r in claude:
        msgs = build_messages(r["post_id"], r["comment_id"])
        print(r["item_id"], [m["role"] for m in msgs], "chars:", [len(m["content"]) for m in msgs])
    print("wrote", path)


if __name__ == "__main__":
    main()
