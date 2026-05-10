"""
main.py — Redtail Intelligence Scraper Pipeline

Usage:
    python main.py                          # scrape current year + report
    python main.py --year 2023              # scrape 2023 data only
    python main.py --scrape-only --year 2022
    python main.py --report-only            # re-generate report from existing data
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(__file__))


def run_scraper(name: str, fn, **kwargs):
    """Run a scraper, emit STATUS lines the dashboard server parses."""
    print(f"STATUS:{name}:running", flush=True)
    try:
        fn(**kwargs)
        print(f"STATUS:{name}:done", flush=True)
    except Exception as e:
        print(f"STATUS:{name}:error", flush=True)
        print(f"  [{name}] Error: {e}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Redtail Intelligence Scraper")
    parser.add_argument("--year",             type=int, default=None,
                        help="Scrape data for a specific year (2022–2025)")
    parser.add_argument("--skip-reddit",      action="store_true")
    parser.add_argument("--skip-steam",       action="store_true")
    parser.add_argument("--skip-play",        action="store_true")
    parser.add_argument("--skip-appstore",    action="store_true")
    parser.add_argument("--skip-forbes",      action="store_true")
    parser.add_argument("--skip-toucharcade", action="store_true")
    parser.add_argument("--skip-pocketgamer", action="store_true")
    parser.add_argument("--report-only",      action="store_true",
                        help="Skip scraping; re-run analysis + report")
    parser.add_argument("--scrape-only",      action="store_true",
                        help="Scrape only; skip analysis + report")
    args = parser.parse_args()

    year = args.year
    year_label = f" [{year}]" if year else ""

    print("=" * 60)
    print(f"  REDTAIL INTELLIGENCE ENGINE{year_label}")
    print("=" * 60)

    # ── Step 1: Scrape ──────────────────────────────────────────
    if not args.report_only:
        from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET

        if not args.skip_reddit:
            if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
                print("STATUS:reddit:done")
                print("\n[reddit] Skipped — no API credentials in .env")
            else:
                from scrapers.reddit_scraper import run as reddit_run
                run_scraper("reddit", reddit_run, year=year)
        else:
            print("STATUS:reddit:done"); print("[reddit] Skipped.")

        if not args.skip_steam:
            from scrapers.steam_scraper import run as steam_run
            run_scraper("steam", steam_run, year=year)
        else:
            print("STATUS:steam:done"); print("[steam] Skipped.")

        if not args.skip_play:
            from scrapers.googleplay_scraper import run as play_run
            run_scraper("googleplay", play_run, year=year)
        else:
            print("STATUS:googleplay:done"); print("[googleplay] Skipped.")

        if not args.skip_appstore:
            from scrapers.appstore_scraper import run as appstore_run
            run_scraper("appstore", appstore_run, year=year)
        else:
            print("STATUS:appstore:done"); print("[appstore] Skipped.")

        if not args.skip_forbes:
            from scrapers.forbes_scraper import run as forbes_run
            run_scraper("forbes", forbes_run, year=year)
        else:
            print("STATUS:forbes:done"); print("[forbes] Skipped.")

        if not args.skip_toucharcade:
            from scrapers.toucharcade_scraper import run as ta_run
            run_scraper("toucharcade", ta_run, year=year)
        else:
            print("STATUS:toucharcade:done"); print("[toucharcade] Skipped.")

        if not args.skip_pocketgamer:
            from scrapers.pocketgamer_scraper import run as pg_run
            run_scraper("pocketgamer", pg_run, year=year)
        else:
            print("STATUS:pocketgamer:done"); print("[pocketgamer] Skipped.")

    if args.scrape_only:
        print("\n  [main] Scrape-only mode — done.")
        return

    # ── Step 2: Analyse ─────────────────────────────────────────
    print("\n" + "=" * 60)
    from analysis.sentiment import run as analysis_run
    from config import DATA_DIR, get_year_dir
    data_dir = get_year_dir(year) if year else DATA_DIR
    analysis = analysis_run(data_dir=data_dir)

    # ── Step 3: Generate (VADER) report ────────────────────────
    print("\n" + "=" * 60)
    from report.generate_report import run as report_run
    out_path = report_run(analysis)

    print("\n" + "=" * 60)
    print(f"  DONE — Report: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
