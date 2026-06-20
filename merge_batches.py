#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge all batch_p*.json produced by turabaev_pipeline.py (across all parts)
into a single deduplicated, page-ordered turabaev_merged.json.

Usage:
  python merge_batches.py ./out                 # merges ./out/**/batch_p*.json
  python merge_batches.py ./out -o all.json
"""
import argparse, glob, json, os, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("indir", help="folder containing batch_p*.json (searched recursively)")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.indir, "**", "batch_p*.json"), recursive=True))
    if not files:
        print("No batch_p*.json found under", args.indir, file=sys.stderr); sys.exit(1)

    entries, seen = [], set()
    for f in files:
        for e in json.load(open(f, encoding="utf-8")):
            # dedup on headword+page+first 30 chars of body (handles overlap/reruns)
            key = (e.get("headword", ""), e.get("page", 0), e.get("body", "")[:30])
            if key in seen:
                continue
            seen.add(key); entries.append(e)

    entries.sort(key=lambda e: (e.get("page", 0), e.get("headword", "")))
    out = args.out or os.path.join(args.indir, "turabaev_merged.json")
    json.dump(entries, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Merged {len(files)} batch files -> {len(entries)} entries -> {out}", file=sys.stderr)

if __name__ == "__main__":
    main()
