"""
main.py — Redtail Intelligence Scraper Pipeline
Runs all scrapers → analysis → report in sequence.

Usage:
    python main.py              # full run (all scrapers)
    python main.py --skip-reddit   # skip Reddit (no API key yet)
    python main.py --report-only   # re-generate report from existing data
"""
import argparse, os, sys

# Make sure sibling modules resolve correctly
sys.path.insert(0, os.path.dirname(__file__))


def main():
    parser = argparse.ArgumentParser(description="Redtail Intelligence Scraper")
    parser.add_argument("--skip-reddit",  action="store_true", help="Skip Reddit scrape")
    parser.add_argument("--skip-steam",   action="store_true", help="Skip Steam scrape")
    parser.add_argument("--skip-play",    action="store_true", help="Skip Google Play scrape")
    parser.add_argument("--skip-appstore",action="store_true", help="Skip App Store scrape")
    parser.add_argument("--report-only",  action="store_true", help="Skip all scraping, regenerate report only")
    args = parser.parse_args()

    print("=" * 60)
    print("  REDTAIL INTELLIGENCE ENGINE — SCRAPER PIPELINE")
    print("=" * 60)

    # ── Step 1: Scrape ──────────────────────────────────────────
    if not args.report_only:
        if not args.skip_reddit:
            from scrapers.reddit_scraper import run as reddit_run
            reddit_run()
        else:
            print("\n[reddit] Skipped.")

        if not args.skip_steam:
            from scrapers.steam_scraper import run as steam_run
            steam_run()
        else:
            print("[steam] Skipped.")

        if not args.skip_play:
            from scrapers.googleplay_scraper import run as play_run
            play_run()
        else:
            print("[googleplay] Skipped.")

        if not args.skip_appstore:
            from scrapers.appstore_scraper import run as appstore_run
            appstore_run()
        else:
            print("[appstore] Skipped.")

    # ── Step 2: Analyse ─────────────────────────────────────────
    print("\n" + "=" * 60)
    from analysis.sentiment import run as analysis_run
    analysis = analysis_run()

    # ── Step 3: Generate report ─────────────────────────────────
    print("\n" + "=" * 60)
    from report.generate_report import run as report_run
    out_path = report_run(analysis)

    print("\n" + "=" * 60)
    print("  DONE")
    print(f"  Report: {out_path}")
    print("  Open in Chrome → Cmd+P → Save as PDF")
    print("=" * 60)


if __name__ == "__main__":
    main()
