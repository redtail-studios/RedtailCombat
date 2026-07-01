"""
Google Trends scraper — pytrends (free, no key). Interest over time + the
*rising* related queries (the real trend signal). Google rate-limits hard, so
this backs off and skips terms it can't fetch rather than crashing.
"""
import time

from config import TREND_TERMS, get_year_dir
from scrapers import score, save


def run(year: int | None = None, log=print) -> list:
    try:
        from pytrends.request import TrendReq
    except Exception:
        log("  [googletrends] pytrends not installed — `pip install pytrends`. Skipping.")
        return save([], get_year_dir(year), "googletrends", log)

    y = year or 2026
    timeframe = f"{y}-01-01 {y}-12-31"
    log(f"[googletrends] {len(TREND_TERMS)} terms over {timeframe}")
    try:
        pt = TrendReq(hl="en-US", tz=0)
    except Exception as e:
        log(f"  [googletrends] init failed: {e}")
        return save([], get_year_dir(year), "googletrends", log)

    records = []
    for term in TREND_TERMS:
        avg = None
        rising = []
        for attempt in range(3):
            try:
                pt.build_payload([term], timeframe=timeframe)
                iot = pt.interest_over_time()
                if iot is not None and not iot.empty and term in iot:
                    avg = round(float(iot[term].mean()), 1)
                rq = pt.related_queries().get(term, {})
                rdf = rq.get("rising")
                if rdf is not None and not rdf.empty:
                    rising = [f"{r['query']} (+{int(r['value'])}%)"
                              for _, r in rdf.head(6).iterrows()]
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(8 * (attempt + 1))  # back off Google's 429
                else:
                    log(f"  [googletrends] '{term}' failed: {type(e).__name__}")
        if avg is None and not rising:
            continue
        text = (f"Google search interest for '{term}' in {y}: avg index {avg}. "
                f"Rising related searches: {'; '.join(rising) if rising else 'none'}.")
        records.append({
            "source": "googletrends", "term": term, "avg_interest": avg,
            "rising_queries": rising, "title": f"Trend: {term} ({y})",
            "text": text, "sentiment": score(text),
        })
        log(f"  [googletrends] {term}: avg {avg}, {len(rising)} rising")
        time.sleep(3)
    return save(records, get_year_dir(year), "googletrends", log)


if __name__ == "__main__":
    run()
