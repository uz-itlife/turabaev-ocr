#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turabaev Russian->Karakalpak dictionary OCR pipeline.

Splits the scanned PDF into page batches ("parts"), OCRs each page
(Russian headwords + Karakalpak Cyrillic translations), parses entries
into structured JSON ready for a dictionary / translation app.

Usage:
  python turabaev_pipeline.py INPUT.pdf --out ./out --dpi 300 --batch 50
  python turabaev_pipeline.py INPUT.pdf --out ./out --first 105 --last 208   # one part

Requirements:
  - tesseract OCR with language data: rus, kaz, uzb_cyrl  (best quality: tessdata_best)
  - poppler-utils (pdftoppm)
  - python: pypdf  (pip install pypdf)

Get the language data (once):
  rus / kaz / uzb_cyrl .traineddata from
  https://github.com/tesseract-ocr/tessdata_best  ->  put in your tessdata dir,
  then set TESSDATA_PREFIX to that folder (or --tessdata).
  kaz + uzb_cyrl together cover the Karakalpak letters қ ғ ң ә ө ү ў ҳ і.
"""
import argparse, os, re, json, subprocess, glob, tempfile, shutil, sys

UP = "А-ЯЁЄІЇҒҚҢӨҮҰҲҺЎӘ"
LO = "а-яёєіїғқңөүұҳһўә"
RE_RUNHEAD = re.compile(rf"^[{UP}]{{2,4}}$")
RE_PAGENUM = re.compile(r"^\s*\d{1,4}\s*$")
RE_HEADWORD = re.compile(rf"^([{UP}][{UP}/]+[{UP}])\b(.*)$")
# grammatical pometы that mark the start of an entry's grammar block
GRAM_KEYS = ("сущ", "прил", "нареч", "глаг", "гл.", "мест", "числ", "союз",
             "предлог", "част", "межд", "сов", "несов", "буд", "наст", "прош",
             "вр.", "л.", "мн.ч", "кратк", "ср.", "м.", "ж.", "разг", "перен")

def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ocr_page(pdf, page, dpi, lang, tessdata, workdir):
    base = os.path.join(workdir, f"p{page}")
    run(["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page), pdf, base])
    imgs = glob.glob(base + "*.png")
    if not imgs:
        return ""
    env = dict(os.environ)
    if tessdata:
        env["TESSDATA_PREFIX"] = tessdata
    out = base + "_ocr"
    subprocess.run(["tesseract", imgs[0], out, "-l", lang, "--psm", "3"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    txt = out + ".txt"
    s = open(txt, encoding="utf-8").read() if os.path.exists(txt) else ""
    for f in imgs + [txt]:
        if os.path.exists(f):
            os.remove(f)
    return s

def clean_lines(raw):
    out = []
    for ln in raw.splitlines():
        s = ln.strip()
        if not s or RE_RUNHEAD.match(s) or RE_PAGENUM.match(s):
            continue
        out.append(s)
    return out

def dehyphenate(lines):
    text = "\n".join(lines)
    text = re.sub(rf"([{LO}{UP}])-\s*\n\s*([{LO}])", r"\1\2", text)
    text = re.sub(rf"([{LO}])-\s+([{LO}])", r"\1\2", text)
    return text

def split_gram(body):
    """Best-effort split: leading grammar block vs. Karakalpak translation."""
    parts = body.split(";", 1)
    head = parts[0]
    if any(k in head.lower() for k in GRAM_KEYS) and len(parts) == 2:
        return head.strip(" ,."), parts[1].strip()
    return "", body.strip()

def parse_text(text, page):
    entries, cur = [], None
    for ln in text.splitlines():
        m = RE_HEADWORD.match(ln)
        if m:
            if cur:
                entries.append(cur)
            lemma = m.group(1)
            cur = {"headword": lemma.replace("/", ""), "lemma": lemma,
                   "_b": [m.group(2).lstrip(" ,")] if m.group(2).strip() else [],
                   "page": page}
        elif cur:
            cur["_b"].append(ln)
    if cur:
        entries.append(cur)
    res = []
    for e in entries:
        body = re.sub(r"\s+", " ", " ".join(e.pop("_b")).strip())
        gram, kaa = split_gram(body)
        if len(e["headword"]) < 2:
            continue
        res.append({"headword": e["headword"], "lemma": e["lemma"],
                    "gram": gram, "translation": kaa, "body": body, "page": e["page"]})
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default="./turabaev_out")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--batch", type=int, default=50)
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--last", type=int, default=0, help="0 = last page of PDF")
    ap.add_argument("--lang", default="rus+kaz+uzb_cyrl")
    ap.add_argument("--tessdata", default=os.environ.get("TESSDATA_PREFIX", ""))
    ap.add_argument("--keep-text", action="store_true", help="also save raw OCR .txt per page")
    args = ap.parse_args()

    from pypdf import PdfReader
    n = len(PdfReader(args.pdf).pages)
    last = args.last or n
    os.makedirs(args.out, exist_ok=True)
    workdir = tempfile.mkdtemp()
    all_entries, batch_buf, batch_start = [], [], args.first

    try:
        for page in range(args.first, last + 1):
            raw = ocr_page(args.pdf, page, args.dpi, args.lang, args.tessdata, workdir)
            if args.keep_text:
                open(os.path.join(args.out, f"page_{page:03d}.txt"), "w",
                     encoding="utf-8").write(raw)
            ents = parse_text(dehyphenate(clean_lines(raw)), page)
            all_entries.extend(ents); batch_buf.extend(ents)
            print(f"page {page}/{last}: {len(ents)} entries", file=sys.stderr)
            if (page - batch_start + 1) >= args.batch or page == last:
                bf = os.path.join(args.out, f"batch_p{batch_start:03d}-{page:03d}.json")
                json.dump(batch_buf, open(bf, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=2)
                batch_buf, batch_start = [], page + 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    merged = os.path.join(args.out, "turabaev_merged.json")
    json.dump(all_entries, open(merged, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\nDONE: {len(all_entries)} entries -> {merged}", file=sys.stderr)

if __name__ == "__main__":
    main()
