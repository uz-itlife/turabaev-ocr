#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Combine dictionary entries that were split into multiple JSON records
during OCR parsing (same headword + page, different body/translation
fragments) into a single entry per (headword, page).

Usage:
  python combine_split_entries.py out/turabaev_merged.json -o out/turabaev_merged_clean.json
"""
import argparse, json, sys
from collections import OrderedDict

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile", help="merged JSON to clean (e.g. turabaev_merged.json)")
    ap.add_argument("-o", "--out", default=None, help="output path (default: <infile>.clean.json)")
    args = ap.parse_args()

    entries = json.load(open(args.infile, encoding="utf-8"))

    groups = OrderedDict()
    for e in entries:
        key = (e.get("headword", ""), e.get("page", 0))
        groups.setdefault(key, []).append(e)

    combined = []
    merged_count = 0
    for (headword, page), parts in groups.items():
        if len(parts) == 1:
            combined.append(parts[0])
            continue
        merged_count += 1
        bodies = [p.get("body", "").strip() for p in parts if p.get("body", "").strip()]
        translations = [p.get("translation", "").strip() for p in parts if p.get("translation", "").strip()]
        grams = [p.get("gram", "").strip() for p in parts if p.get("gram", "").strip()]
        combined.append({
            "headword": headword,
            "lemma": parts[0].get("lemma", headword),
            "gram": grams[0] if grams else "",
            "translation": " | ".join(dict.fromkeys(translations)),
            "body": " | ".join(dict.fromkeys(bodies)),
            "page": page,
        })

    combined.sort(key=lambda e: (e.get("page", 0), e.get("headword", "")))

    out = args.out or args.infile.replace(".json", ".clean.json")
    json.dump(combined, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{len(entries)} entries -> {len(combined)} entries "
          f"({merged_count} split entries combined) -> {out}", file=sys.stderr)

if __name__ == "__main__":
    main()
