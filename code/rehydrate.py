#!/usr/bin/env python3
"""
Rebuild ToMTrace post and comment text from Reddit IDs.

ToMTrace releases Reddit IDs, model outputs, and human labels, but not the
original post/comment text. This script fetches the text from the Arctic Shift
Reddit archive (https://arctic-shift.photon-reddit.com), which serves archived
public Reddit content by ID, and writes a rehydrated copy of the dataset.

Usage:
    python3 rehydrate.py data/tomtrace.jsonl data/tomtrace_rehydrated.jsonl

Items whose post or comment has since been deleted from the archive are kept
with empty text and listed at the end. Standard library only.
"""

import html
import json
import sys
import time
import urllib.parse
import urllib.request

API = "https://arctic-shift.photon-reddit.com/api"


def fetch(kind, ids, fields):
    """kind: 'posts' or 'comments'. Returns {id: record}."""
    out = {}
    ids = list(ids)
    for i in range(0, len(ids), 100):
        q = urllib.parse.urlencode({"ids": ",".join(ids[i:i + 100]), "fields": ",".join(fields)})
        req = urllib.request.Request(f"{API}/{kind}/ids?{q}", headers={"User-Agent": "tomtrace-rehydrate/1.0"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.load(r).get("data", [])
                break
            except Exception as e:  # rate limit or transient error
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        for rec in data:
            out[rec["id"]] = rec
        time.sleep(0.5)
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    items = [json.loads(l) for l in open(src, encoding="utf-8")]
    posts = fetch("posts", {it["post_id"] for it in items}, ["id", "title", "selftext"])
    comments = fetch("comments", {it["comment_id"] for it in items}, ["id", "body"])
    missing = []
    with open(dst, "w", encoding="utf-8") as fh:
        for it in items:
            p, c = posts.get(it["post_id"]), comments.get(it["comment_id"])
            clean = lambda t: html.unescape(html.unescape(t or ""))  # archive double-escapes entities
            it["post_title"] = clean(p.get("title")) if p else ""
            it["post_text"] = clean(p.get("selftext")) if p else ""
            it["comment_text"] = clean(c.get("body")) if c else ""
            if not p or not c or it["post_text"] in ("[deleted]", "[removed]") \
                    or it["comment_text"] in ("[deleted]", "[removed]"):
                missing.append((it["post_id"], it["comment_id"]))
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"Rehydrated {len(items) - len(missing)}/{len(items)} items -> {dst}")
    for m in missing:
        print("  missing or deleted:", *m)


if __name__ == "__main__":
    main()
