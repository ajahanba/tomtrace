#!/usr/bin/env python3
"""
Judge calls through the Claude Code CLI in headless mode, using the logged-in
subscription (no API key).

  call_judge(system, user_text, cache_key) -> (text, meta)

Every call is cached to raw/<cache_key>.json (full input, output, CLI-reported
model, CLI version, flags, timestamp); a cached call is never repeated.
Calls run from an empty sandbox directory with ANTHROPIC_API_KEY removed from
the environment, are paced at least MIN_GAP seconds apart, and stop cleanly
(UsageLimit) when the CLI reports a usage or session limit.
"""

import functools
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SANDBOX = os.path.join(HERE, "_cli_sandbox")
MODEL = "claude-sonnet-4-6"
MIN_GAP = 3.0
FLAGS = ["-p", "--output-format", "json", "--model", MODEL, "--tools", "",
         "--safe-mode", "--no-session-persistence"]
HEADER = ("Below is a conversation in progress. Continue it by writing ONLY the assistant's "
          "response to the final user turn, following its instructions exactly.\n\n")
LIMIT_RX = re.compile(r"(session|usage|rate)[ -]limit|hit your limit|limit reached", re.I)

_last_call = [0.0]


class UsageLimit(RuntimeError):
    pass


def cli_path():
    return os.environ.get("CLAUDE_CLI") or os.environ.get("CLAUDE_CODE_EXECPATH") or "claude"


@functools.lru_cache(maxsize=1)
def cli_version():
    r = subprocess.run([cli_path(), "--version"], capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


STEP4_HEADER = (HEADER.rstrip("\n") + " Write ONLY the assistant's Step 4 answer, then stop: do not write any "
                "later turns or turn labels. End your answer with the line \"END OF STEP 4\".\n\n")
# STEP4_HEADER is used only for the regenerated Step 4 calls of the follow-up run (run_step45.py).


def flatten(messages, header=HEADER):
    """Render [system, user1, asst1, ..., userN] as one user message (system excluded)."""
    parts, step = [], 0
    for m in messages:
        if m["role"] == "system":
            continue
        if m["role"] == "user":
            step += 1
            parts.append(f"[USER - Step {step}]\n{m['content']}")
        else:
            parts.append(f"[ASSISTANT - Step {step}]\n{m['content']}")
    return header + "\n\n".join(parts)


ENV_OVERRIDES = {"MAX_THINKING_TOKENS": "0"}   # no extended thinking (original chains had none)


def _env():
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env.update(ENV_OVERRIDES)
    return env


def call_judge(system, user_text, cache_key):
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(SANDBOX, exist_ok=True)
    path = os.path.join(RAW, f"{cache_key}.json")
    if os.path.exists(path):
        rec = json.load(open(path))
        return rec["output_text"], rec
    wait = MIN_GAP - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    cmd = [cli_path()] + FLAGS + ["--system-prompt", system]
    started = datetime.now(timezone.utc).isoformat()
    r = subprocess.run(cmd, input=user_text, capture_output=True, text=True, timeout=900,
                       cwd=SANDBOX, env=_env())
    _last_call[0] = time.time()
    raw_out = r.stdout.strip()
    try:
        js = json.loads(raw_out)
    except json.JSONDecodeError:
        js = None
    text = (js or {}).get("result", "") if js else raw_out
    if r.returncode != 0 or (js and js.get("is_error")) or not text:
        blob = f"{raw_out} {r.stderr}"
        if LIMIT_RX.search(blob):
            raise UsageLimit(blob[-300:])
        raise RuntimeError(f"CLI call failed (rc={r.returncode}): {blob[-300:]}")
    models = sorted((js or {}).get("modelUsage", {}).keys())
    rec = {
        "cache_key": cache_key, "timestamp_utc": started, "cli_version": cli_version(),
        "flags": FLAGS + ["--system-prompt", "<system prompt below>"], "requested_model": MODEL,
        "reported_models": models, "env_overrides": ENV_OVERRIDES,
        "usage_by_model": {m: {k: u.get(k) for k in ("inputTokens", "cacheCreationInputTokens",
                                                      "cacheReadInputTokens", "outputTokens", "thinkingTokens")}
                           for m, u in (js or {}).get("modelUsage", {}).items()},
        "system_prompt": system, "user_text": user_text,
        "user_text_sha256": hashlib.sha256(user_text.encode()).hexdigest(),
        "output_text": text, "cli_json": js,
    }
    json.dump(rec, open(path, "w"), indent=1, ensure_ascii=False)
    return text, rec
