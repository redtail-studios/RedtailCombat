#!/usr/bin/env python3
"""
scrape.py — local CLI to collect data from all free platforms.

Run this locally to refresh the dataset, then commit ai_engine/data/ so the
deployed app (Vercel) can analyse it.

  python scrape.py                       # all platforms, current year (2026)
  python scrape.py --year 2024           # a specific year
  python scrape.py --year 2024 --only steam,googleplay
  python scrape.py --year 2024 --skip reddit
"""
import argparse
import importlib

from config import PLATFORM_IDS, SUPPORTED_YEARS


def main():
    ap = argparse.ArgumentParser(description="AI engine — free-platform scraper")
    ap.add_argument("--year", type=int, default=2026,
                    help=f"year to tag data with {SUPPORTED_YEARS}")
    ap.add_argument("--only", default="", help="comma list of platforms to run")
    ap.add_argument("--skip", default="", help="comma list of platforms to skip")
    args = ap.parse_args()

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    targets = [p for p in PLATFORM_IDS
               if (not only or p in only) and p not in skip]

    print("=" * 56)
    print(f"  AI ENGINE SCRAPER — year {args.year}")
    print(f"  platforms: {', '.join(targets)}")
    print("=" * 56)

    for pid in targets:
        try:
            mod = importlib.import_module(f"scrapers.{pid}")
            mod.run(year=args.year)
        except Exception as e:
            print(f"  [{pid}] FAILED: {e}")

    print("\nDone. Commit ai_engine/data/ to deploy this dataset.")


if __name__ == "__main__":
    main()
