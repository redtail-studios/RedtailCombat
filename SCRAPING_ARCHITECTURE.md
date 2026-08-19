# Lore scraping architecture

This explains how scraping works for the Lore subsystem, particularly the
**deployed** path — which AWS services get called, in what order, by which
process, and what to do when something breaks. It assumes no prior context;
if you're picking this up cold, read section 1 first, then use the rest as
reference.

Two code paths exist side by side, both live in `server.py`, branching on
`DEPLOYED` (`config.DEPLOYED = bool(os.getenv("VERCEL"))`):

- **Local** (`DEPLOYED=False`): scraping runs in a background thread inside
  the same process, writes straight to `lore_data/` on disk, and
  `manifest.rebuild()` globs those files to build `lore_data/manifest.json`.
  This still works exactly as it always has — nothing below applies to it.
- **Deployed** (`DEPLOYED=True`): this is what the rest of this document
  covers. Vercel's serverless functions have no writable filesystem and no
  thread that survives past the HTTP response, so scraping is a real
  asynchronous pipeline: S3 + SQS + a separate Lambda worker.

## 1. How a deployed scrape actually happens

There are two ways a scrape gets kicked off, both converging on the same
`storage.enqueue_missing_platforms()` helper and the same SQS → worker Lambda
pipeline:

- **Weekly, automatic** — an AWS EventBridge Scheduler rule invokes a small,
  separate Lambda (`lore_engine/scheduler.py`) directly, entirely bypassing
  Vercel. This is the primary path now; nobody needs to click anything.
- **Manual, ops-only** — `POST /api/lore/scrape` (`server.py`'s
  `_start_scrape_deployed()`), gated by `LORE_PASSWORD` and hidden from the
  normal `lore.html` UI (only shown with `?ops=1` in the URL). Useful for
  forcing an out-of-band re-scrape without waiting for next week's schedule.

Walking through one full cycle, in order:

1. Either the EventBridge schedule fires `scheduler.handler()` (weekly, no
   input needed), or someone hits `POST /api/lore/scrape` with a year via
   the ops UI.
2. Both paths call `storage.enqueue_missing_platforms(year, force=...)`, but
   the scheduler now calls it for **every** year in `config.SUPPORTED_YEARS`,
   not just the current one:
   - **Current year** (`storage.current_year()`) → `force=True`. The weekly
     cadence *is* the freshness mechanism for this one, so every platform
     gets re-enqueued regardless of the TTL.
   - **Every past year** → `force=False` — a backfill, not a re-scrape. Past
     years are frozen annual snapshots (see §"Freshness / TTL"): once a
     platform has *any* data for a past year, `is_cached_fresh()` treats it
     as fresh forever, so `force=False` only enqueues platforms that are
     genuinely missing — one that errored out every time (e.g.
     `appcharts`/`igdb`/`gdelt` before a worker packaging bug was fixed) or
     one added after that year was last scraped. Once nothing is missing for
     a past year, this step enqueues nothing for it — cheap to run every
     week.
   - The ops UI's manual path always passes `force=False`, for whatever
     single year the user picks.
   For each of the 18 platforms in `config.PLATFORM_IDS`,
   `storage.is_cached_fresh(year, platform)` (a cheap S3 `head_object`)
   decides whether that platform already has fresh data for that year.
   Platforms that are already fresh are skipped — nothing gets re-scraped or
   re-enqueued for them.
3. For every platform that's enqueued, `enqueue_missing_platforms()` writes a
   `"queued"` status marker (`storage.put_status`) and sends one SQS message
   (`storage.enqueue_scrape`) — message body is just `{"year": ..., "platform": ...}`.
   Neither caller waits for scraping itself; the ops API call returns
   immediately, and the scheduler Lambda's job is done as soon as messages
   are on the queue.
4. The SQS queue has a Lambda function (`lore_engine/worker.py`) subscribed
   to it via an event source mapping. AWS delivers each message to a Lambda
   invocation — one message, one `(year, platform)` job, one invocation
   (batch size 1).
5. `worker.py`'s `_process_one()` marks status `"running"`, dynamically
   imports `scrapers.<platform>`, and calls its `run(year, log=print)` —
   **completely unmodified** scraper code, the same functions local scraping
   uses. `print()` output lands in CloudWatch.
6. On success, the worker uploads the returned records to S3
   (`storage.put_records`) and marks status `"done"` (or `"empty"` if the
   scraper returned nothing). On any exception, it tries to mark status
   `"error"` and re-raises — letting SQS's own retry/DLQ policy handle it,
   rather than swallowing the failure.
7. Meanwhile, the frontend (or anyone) polls `GET /api/lore/scrape/status?year=`,
   which calls `storage.scrape_status_snapshot()` — this reads every
   platform's status marker from S3 directly; there's no shared memory
   between the API process and the worker, so S3 *is* the shared state.
8. `GET /api/lore/status` (the manifest / "last scraped" view) calls
   `storage.compute_manifest()`, which lists everything under the S3 data
   prefix and reads per-object `count` metadata via `head_object` — it does
   **not** maintain a separately-written `manifest.json` object, specifically
   to avoid a read-modify-write race if two workers finish around the same
   time (see §"Known gotchas").
9. Later, `POST /api/lore/report` triggers `analysis.py`, which reads
   platform data straight from S3 via `storage.get_cached_records()`. This
   path is **read-only** — report generation never scrapes, never enqueues;
   a missing or stale platform is just silently skipped, same as a missing
   local file would be.

Note on consistency while a scrape is running: `put_records()` (step 6) is a
single `PutObject` per `(year, platform)` key, which S3 already makes atomic
— so every reader always sees either that platform's last-good data or its
newly-finished data, never a half-written mix. The swap is **per-platform**,
not all-or-nothing across the whole weekly run: if one platform (e.g. Reddit)
errors out, the other 17 still update normally and nothing blocks on it.

### Freshness / TTL

Only the **current calendar year** expires. Past years, once scraped, are
cached forever — there's no reason to re-scrape 2023. Freshness is an
app-level check (`storage._is_fresh`) against the S3 object's `LastModified`
timestamp compared to `LORE_CACHE_TTL_SECONDS` (default 7 days) — there is
no S3 bucket lifecycle policy involved; nothing physically deletes old
objects, they just get treated as a cache miss and overwritten on the next
scrape.

### Incremental scraping (current year only)

Most platforms fully overwrite their data on every scrape — correct, because
most of what they capture is a **live metric that changes for records
already seen** (review/owner counts, chart rank, hype score). Re-fetching
the current state is the only way to keep those accurate. Two shapes of
exception exist, both driven by the same `since` cursor: before calling the
scraper, the worker reads the existing data's `LastModified` via
`storage.get_last_scraped()` and passes it as `since` to `run()`.
First-ever scrape for a `(year, platform)` → no existing object →
`since=None` → every scraper falls back to today's full-year fetch,
unchanged.

**Flat list, immutable records** — `hackernews`, `gamenews`, `gdelt`
(`worker.py`'s `INCREMENTAL_MERGE_KEYS`). A news article or forum story
doesn't change once captured, each has a stable unique key (`id` or `url`),
and re-fetching the full year every week was mostly re-downloading content
already stored. Each scraper narrows its own query by `since` where the
source supports it server-side (Algolia's `numericFilters` for hackernews,
GDELT's `startdatetime`) — a real reduction in what gets fetched, not just
what gets kept. `gamenews`'s RSS feeds have no date-range query at all, so
`since` there only trims what gets kept client-side. After the scraper
returns, the worker merges via `storage.merge_by_key()` — existing entries
win on a key collision, genuinely new keys get appended.

**Per-app records with a live-metric/append-only split** — `steam`,
`appstore`, `googleplay` (`worker.py`'s `INCREMENTAL_NESTED_MERGE_KEYS`).
These records mix live app-level metrics (owners, installs, positive/negative
counts) with a nested `reviews` list that's append-only once a review
exists. A flat merge doesn't fit — `storage.merge_nested_by_key()` matches
records by `app_id`, always takes the *new* fetch's top-level fields (fresh
metrics), and only merges the nested list by a review-level key:
- `steam`: reviews already carry `timestamp_created`; `_reviews()`'s
  existing "stop once a page predates `year`" early-exit was extended to
  also stop once a page predates `since` — real fewer requests, not just
  fewer kept. Reviews didn't previously carry a stable id at all
  (`recommendationid` exists in Steam's API but wasn't captured) — added,
  since merge-by-key needs one.
- `googleplay`: reviews are already fetched `Sort.NEWEST`; same early-exit
  pattern once a review's `at` predates `since`. Watch for the naive/aware
  datetime mismatch — `google-play-scraper` returns naive datetimes, while
  `since` (from S3's `LastModified`) is UTC-aware; compare after stripping
  tzinfo from `since` rather than assuming both sides match.
- `appstore`: no date field exists on iTunes RSS reviews at all (documented
  in the code already) — `since` is accepted for interface consistency but
  can't shrink the fetch; same request cost as before every time. Only wins
  the "no duplicate accumulation" part, via the RSS entry's own `id`.

`wikipedia` was considered and rejected: its "current month" pageview
bucket is itself a live number that grows until the month ends — summing
"new months since last scrape" into a running total would double-count the
in-progress month every week until it rolls over. Fixing that correctly
needs to track which months are "finalized" vs. still in-progress, for a
scraper that already only takes ~5-8 seconds to run in full. Not worth it
for what it'd save.

## 2. What each AWS service is for

| Service | Used for | Written by | Read by |
|---|---|---|---|
| **S3** | The actual data store: scraped records (`<prefix>/data/<year>/<platform>.json`) and per-platform job status (`<prefix>/status/<year>/<platform>.json`) | The Lambda worker (`put_records`, `put_status`) and the API/scheduler (`put_status` when enqueueing) | The API (status polling, manifest, report generation) and the worker (freshness isn't checked worker-side — see gotcha below) |
| **SQS** | The work queue — one message per `(year, platform)` job that needs scraping | The API (ops fallback) and the scheduler Lambda (weekly), both via `storage.enqueue_missing_platforms()` → `enqueue_scrape()` | The worker Lambda's event source mapping (AWS-managed; not code you'll find in this repo) |
| **Lambda (worker)** | Runs the actual scraper code, off the request/response cycle entirely | — | Triggered by SQS |
| **Lambda (scheduler)** | Fans out the weekly scrape — no scraping itself, just enqueues | — | Triggered by EventBridge Scheduler |
| **EventBridge Scheduler** | The weekly cron trigger (e.g. `cron(0 6 ? * MON *)`) that invokes the scheduler Lambda directly, independent of Vercel | — | AWS-managed |
| **IAM** | *Three* separate credential paths — see below | — | — |

**IAM is the part most likely to bite you**, because there are three
completely independent credential paths that all need to work:

- **The Vercel API process** authenticates to AWS with static credentials
  (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` env vars) — Vercel functions
  can't assume an IAM role the way Lambda can.
- **The Lambda worker** authenticates via its own execution role
  (`redtail-scraper-role-nqxjyv05` in the current test setup), which needs:
  - `s3:PutObject`, `s3:GetObject` on the **object-level ARN**
    (`arn:...:bucket/*`) — note there's no `s3:HeadObject` IAM action; the
    `HeadObject` *API operation* authorizes against the `s3:GetObject`
    *permission*, same as `GetObject` itself.
  - `s3:ListBucket` on the **bucket-level ARN** (`arn:...:bucket`, no `/*`)
    — this one's easy to skip since nothing obviously needs it, but without
    it S3 masks a missing key as `403 Forbidden` instead of `404 Not Found`
    on `HeadObject`/`GetObject` (deliberate: it stops callers from probing
    which keys exist). A policy with only the object-level ARN grants
    `GetObject`/`PutObject` but silently breaks any "does this exist yet"
    check.
  - `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` on
    the queue.
  - `AWSLambdaBasicExecutionRole` for CloudWatch logs.
- **The scheduler Lambda** (`redtail-scrape-scheduler-role`) is narrower —
  it never downloads object bodies or dequeues, so it only needs:
  - `s3:GetObject`, `s3:PutObject` on the bucket's **object-level** ARN
    (freshness checks + status markers).
  - `s3:ListBucket` on the bucket's **bucket-level** ARN. **This is
    load-bearing, not optional, for the past-year backfill specifically**:
    `force=False` calls `is_cached_fresh()` → `head_object()` for every one
    of the 18 platforms across every past year, on every weekly run — and
    for a genuinely missing platform (the exact case backfill exists to
    catch), S3 returns `403` instead of `404` without `ListBucket`, which
    `storage._not_found()` doesn't recognize as a cache miss, so it
    re-raises instead of enqueueing. Confirmed by testing: the role had
    `GetObject`+`PutObject` but no `ListBucket`, and every backfill call
    failed with `403` until `ListBucket` was added.
  - `sqs:SendMessage` on the queue.
  - `AWSLambdaBasicExecutionRole` for CloudWatch logs.
  - Separately, the **EventBridge Scheduler schedule** itself needs its own
    invoke-only role, scoped to `lambda:InvokeFunction` on just this
    function's ARN — don't reuse the scheduler Lambda's own execution role
    for this, they're different principals (EventBridge invoking Lambda vs.
    Lambda itself calling S3/SQS).

## 3. Local vs. deployed, endpoint by endpoint

| Endpoint | Local (`DEPLOYED=False`) | Deployed (`DEPLOYED=True`) |
|---|---|---|
| `GET /api/lore/status` | Reads `lore_data/manifest.json` off disk | `storage.compute_manifest()` — live S3 listing |
| `POST /api/lore/scrape` | Spawns a background thread, scrapes all 18 platforms sequentially in-process | `_start_scrape_deployed()` → `storage.enqueue_missing_platforms(year, force=False)` — the ops-only fallback, hidden behind `lore.html?ops=1` |
| *(weekly, automatic)* | — n/a — | EventBridge Scheduler → `scheduler.handler()` → `force=True` enqueue for the current year **and** a `force=False` backfill enqueue for every other year in `config.SUPPORTED_YEARS`, no HTTP involved at all |
| `GET /api/lore/scrape/status` | Reads the in-memory `_scrape` dict | `storage.scrape_status_snapshot()` — reads S3 status markers |
| `POST /api/lore/report` | `analysis.py` reads `lore_data/<year>/<platform>_data.json` off disk | `analysis.py` reads via `storage.get_cached_records()` |
| Scraper modules (`scrapers/*.py`) | Unchanged either way — `run()` doesn't know or care who's calling it | Unchanged either way |

## 4. Configuration reference

| Env var | Read by | Controls |
|---|---|---|
| `VERCEL` | API (`config.DEPLOYED`) | Set automatically by Vercel — this is *the* switch between local/deployed behavior |
| `AWS_LAMBDA_FUNCTION_NAME` | Worker (`config.IS_LAMBDA`) | Set automatically by the Lambda runtime — redirects `get_year_dir()` to `/tmp` so scrapers' local-disk write doesn't fail on Lambda's read-only filesystem |
| `AWS_BUCKET` | API, worker, scheduler | Which S3 bucket everything lives in |
| `AWS_REGION` | API, worker, scheduler | Region for S3/SQS clients (default `us-east-1`) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | API only | Vercel's static AWS credentials (both Lambdas use their own execution role instead) |
| `LORE_SCRAPE_QUEUE_URL` | API, scheduler | The SQS queue to enqueue into — the worker never needs this, it's invoked *by* SQS, not polling it |
| `LORE_S3_PREFIX` | API, worker, scheduler | Root S3 key prefix (default `"lore"`). **Override this for any test deployment** (e.g. `lore-test`) so test data can never collide with production's keyspace in the same bucket — this must match across the API's env, the worker Lambda's env, *and* the scheduler Lambda's env, or they'll silently read/write different locations |
| `LORE_CACHE_TTL_SECONDS` | API, scheduler (only matters when `force=False`, i.e. never for the scheduler's own calls, but keep it consistent anyway) | Current-year freshness window (default 604800 = 7 days) |
| `LORE_PASSWORD` | API only | Gates the scrape/report/snapshot endpoints — unrelated to AWS |

## 5. Known gotchas

Things that took real debugging time to figure out — check here before
re-deriving them from scratch:

- **Lambda "Handler" setting must exactly match the deployed module.** If it's
  still the console default (`lambda_function.lambda_handler`) instead of
  `worker.handler`, every invocation fails at `INIT` before any of our code
  runs — `_process_one`'s try/except can't catch this, because it never
  starts. Symptom: SQS messages sit "in flight" forever, status never moves
  past `"queued"`. Check with `aws lambda get-function-configuration
  --function-name <name> --query Handler`.
- **250 MB uncompressed zip limit** for Lambda deployment packages. The full
  `requirements.txt` (which also serves the FastAPI app — `fastapi`,
  `uvicorn[standard]`, `anthropic`, `openai`, `awscli`) blows past this. The
  worker only needs what the scrapers actually import: see
  `requirements-worker.txt`, deliberately excluding `boto3`/`botocore` too
  (every standard Lambda Python runtime already ships them). `pytrends`
  (for `googletrends`) still pulls in `pandas`+`numpy`, which dominates the
  package size (~145 MB alone) but fits once the unrelated web-app deps are
  gone.
- **Compressed zips over 50 MB can't use `--zip-file` directly** — stage
  through S3 first (`aws s3 cp` then `update-function-code --s3-bucket
  ... --s3-key ...`).
- **`zip` updates an existing archive instead of overwriting it.** If a
  stale zip from a previous (larger) build is sitting at your output path,
  re-running `zip -r archive.zip .` merges old and new entries instead of
  replacing them — always `rm -f` the zip before rebuilding.
- **`compute_manifest()` deliberately doesn't maintain a `manifest.json`
  object in S3** — it's computed live from a `list_objects_v2` + per-object
  `head_object` metadata read every time it's called. This avoids a
  read-modify-write race between two Lambda invocations finishing different
  platforms of the same year around the same time, at the cost of a
  somewhat more expensive read. Don't "optimize" this into a cached
  manifest object without re-solving that race.
- **Reddit specifically cannot be fixed by more compute or a bigger
  timeout.** Its anonymous RSS endpoint returns `x-ratelimit-remaining=0.0`
  on nearly every request from any AWS-owned IP — including a dedicated
  Elastic IP behind a NAT Gateway, which was tried and made no measurable
  difference. This points to ASN/IP-range-based throttling (cloud vs.
  residential), not per-IP noise, so trimming request count or moving to a
  different IP within AWS's address space won't help. The real fix is
  Reddit's OAuth API (`REDDIT_CLIENT_ID`/`SECRET` already exist in `.env`
  but `reddit.py` doesn't use them) — currently blocked by Reddit's 2025+
  "Responsible Builder Policy," which replaced self-service app creation
  with a manual approval queue. Until/unless that's resolved, treat reddit
  as a special case (e.g. scrape it locally from a residential IP and
  upload the result to S3 manually) rather than expecting it to work
  through the Lambda pipeline.
- **Reddit data only exists for the current year — scraping a past year
  reliably comes back empty.** `reddit.py` only ever fetches `/hot/.rss`
  (see its module docstring for why `/top/.rss?t=year` was deliberately
  skipped too); "hot" reflects what's active *right now*, not an archive, so
  its posts are almost all from the current year regardless of what `year`
  was requested. `run()`'s year filter (`reddit.py`'s `if year and year <
  NOW_YEAR and ...`) is a no-op for the current year but, for any earlier
  year, drops nearly every post it fetched — there's essentially nothing
  left from years-old "hot" posts to keep. This is a data-source limitation,
  not a bug: there's no fix without a different Reddit endpoint (Reddit's
  RSS has no real date-range query; only the OAuth search API does, which is
  the same OAuth migration already called out above for the rate-limit
  issue). Until that migration happens, don't expect Reddit data for
  `SUPPORTED_YEARS` entries other than the current one.
- **A stuck job with no redrive policy retries forever, silently.** On
  2026-08-03, `redtail-lore-queue` had no `RedrivePolicy` at all — a DLQ
  (`redtail-dlq`) existed but was never wired up. Meanwhile `reddit.py` had
  no internal time limit, so under sustained rate-limiting it would run past
  the worker's 900s Lambda timeout and get hard-killed mid-scrape. A
  timed-out invocation never deletes its SQS message, so once the queue's
  1800s `VisibilityTimeout` elapsed the same job was redelivered and timed
  out again — forever, ~900 GB-seconds per ~30-minute cycle, with nothing
  in the logs looking like an error (`Task timed out` doesn't even show up
  as a log *message* — check the `REPORT` line's `Status: timeout` field
  instead). This ran for hours before an AWS Free Tier usage alert (85% of
  the account's monthly Lambda-GB-second allowance) surfaced it. Two fixes,
  both needed:
  - `reddit.py` now tracks wall-clock time against `TIME_BUDGET_SECONDS`
    (720s) and returns whatever it's collected so far instead of running
    until killed — the same pattern any slow/rate-limited scraper should
    follow, since a killed invocation is strictly worse than a partial
    result (no data *and* it keeps retrying).
  - `redtail-lore-queue` now has a real `RedrivePolicy`
    (`maxReceiveCount: 3` → `redtail-dlq`), so even a scraper that somehow
    still hangs is bounded at ~2,700 GB-seconds instead of running forever.
  - If you see a platform stuck on `"running"` for an implausibly long time,
    check `ApproximateNumberOfMessagesNotVisible` on the queue and the
    worker's `REPORT` log lines for `Status: timeout` before assuming it's
    just slow.

## 6. Runbook

**Actual deployed resource names (test environment, account 512190911607,
`us-east-1`, `LORE_S3_PREFIX=lore-test`)** — the commands below use
`<placeholder>` names; here's what they map to today:

| Placeholder | Actual name |
|---|---|
| `<worker-fn>` | `redtail-scraper` |
| `<scheduler-fn>` | `redtail-scraper-scheduler` — note the extra "r" (typo from initial console setup, left as-is rather than deleting/recreating the function) |
| scheduler's execution role | `redtail-scrape-scheduler-role` |
| EventBridge Scheduler's invoke role | `redtail-scrape-scheduler-invoke-policy` — also misnamed (ends in `-policy`, not `-role`), just be aware when looking it up in IAM |
| EventBridge schedule name | `redtail-weekly-scrape` |
| scheduler's inline S3/SQS policy | `redtail-scheduler-bucket` on `redtail-scrape-scheduler-role` — as of the historical-year backfill, this **must** include `s3:GetObject` (not `HeadObject` — that's not a real IAM action) **and** `s3:ListBucket` on the bare bucket ARN (not just `bucket/*`). Originally had only `PutObject`+`SendMessage`, which fails the backfill with `403` on any genuinely-missing platform — see §2. |

**Rebuild and redeploy the worker after a code change:**

The `--platform`/`--python-version` flags below MUST match the Lambda's
actual configured runtime (`aws lambda get-function-configuration
--function-name <worker-fn> --query Runtime`) — currently `python3.14`.
Compiled deps (numpy/pandas, pulled in by pytrends) ship as `.so` files
tagged to one CPython ABI; a mismatch doesn't error at build time, it fails
*silently* at import time inside the Lambda (caught by scrapers' own
broad `except Exception` around their imports) and gets misreported as
"not installed" — see the 2026-08-19 incident where this exact drift
(built for 3.11, deployed to a 3.14 runtime) killed the googletrends
scraper for weeks without ever raising a Lambda error or CloudWatch alarm.
`manylinux2014` doesn't have cp314 wheels for numpy/pandas yet; use
`manylinux_2_28_x86_64` instead.
```bash
rm -rf /tmp/lore-worker-build && mkdir -p /tmp/lore-worker-build
cp lore_engine/{worker,storage,config,manifest}.py /tmp/lore-worker-build/
cp -r lore_engine/scrapers /tmp/lore-worker-build/
pip install -r requirements-worker.txt \
  --platform manylinux_2_28_x86_64 --implementation cp --python-version 3.14 \
  --only-binary=:all: -t /tmp/lore-worker-build/

rm -f /tmp/lore-worker.zip
cd /tmp/lore-worker-build && zip -r -q /tmp/lore-worker.zip . -x '*.pyc' '*/__pycache__/*'

# if the compressed zip is over 50MB, stage through S3 instead of --zip-file:
aws lambda update-function-code --function-name <worker-fn> --zip-file fileb:///tmp/lore-worker.zip
aws lambda wait function-updated --function-name <worker-fn>
```

**Rebuild and redeploy the scheduler after a code change:**
```bash
rm -rf /tmp/lore-scheduler-build && mkdir -p /tmp/lore-scheduler-build
cp lore_engine/{scheduler,storage,config}.py /tmp/lore-scheduler-build/
pip install -r requirements-scheduler.txt \
  --platform manylinux_2_28_x86_64 --implementation cp --python-version 3.14 \
  --only-binary=:all: -t /tmp/lore-scheduler-build/

rm -f /tmp/lore-scheduler.zip
cd /tmp/lore-scheduler-build && zip -r -q /tmp/lore-scheduler.zip . -x '*.pyc' '*/__pycache__/*'
aws lambda update-function-code --function-name <scheduler-fn> --zip-file fileb:///tmp/lore-scheduler.zip
aws lambda wait function-updated --function-name <scheduler-fn>
```
This package is small (no scrapers, no pandas/numpy) — it'll never hit the
250 MB/50 MB limits described above, so `--zip-file` directly is fine.

**Trigger the weekly job manually** (bypasses the EventBridge schedule
entirely, useful for testing the scheduler Lambda itself):
```bash
aws lambda invoke --function-name <scheduler-fn> --payload '{}' /tmp/result.json
cat /tmp/result.json   # {"queued_by_year": {"2026": [...force=True...], "2022": [...gaps only...], ...}}
curl -s "https://<host>/api/lore/scrape/status?year=2026" | python3 -m json.tool
aws logs tail /aws/lambda/<worker-fn> --since 5m
```

**Change the weekly cadence:**
```bash
aws scheduler update-schedule --name <schedule-name> \
  --schedule-expression 'cron(0 6 ? * MON *)'   # UTC; adjust day/time as needed
```

**Trigger a scrape via the ops fallback and watch it** (only for
out-of-band/manual re-runs — the weekly schedule above is the primary path
now):
```bash
curl -X POST https://<host>/api/lore/scrape -H 'Content-Type: application/json' \
  -d '{"year": 2026, "password": "<LORE_PASSWORD>"}'
curl -s "https://<host>/api/lore/scrape/status?year=2026" | python3 -m json.tool
aws logs tail /aws/lambda/<worker-fn> --since 5m
```

**Test one `(year, platform)` job directly, bypassing the freshness check
and the API entirely** (useful when a platform is already cached "fresh"
but you want to force a real re-run):
```bash
echo '{"Records":[{"body":"{\"year\": 2026, \"platform\": \"steam\"}"}]}' > /tmp/test-event.json
aws lambda invoke --function-name <worker-fn> --payload fileb:///tmp/test-event.json \
  --cli-read-timeout 900 /tmp/result.json
```

**Clear stuck/duplicate messages** (e.g. after fixing a bug that was
causing retries): `aws sqs purge-queue --queue-url <queue-url>`

**Testing safely without touching production data**: set `LORE_S3_PREFIX`
to something like `lore-test` on whatever deployment you're testing against,
and use a separate SQS queue + Lambda for that deployment. Never point a
test deployment's `LORE_SCRAPE_QUEUE_URL` at the production queue.

## 7. Source of truth

This document orients; the code is authoritative. Start here:
- `lore_engine/storage.py` — all S3/SQS access, including
  `enqueue_missing_platforms()` (shared by the ops endpoint and the scheduler)
  and `get_last_scraped()`/`get_raw_records()`/`merge_by_key()`/
  `merge_nested_by_key()` (incremental scraping support)
- `lore_engine/worker.py` — the SQS-triggered Lambda that does the actual
  scraping; `INCREMENTAL_MERGE_KEYS` / `INCREMENTAL_NESTED_MERGE_KEYS` list
  which platforms get the `since` cursor + merge instead of a full overwrite
- `lore_engine/scheduler.py` — the EventBridge-triggered Lambda that fans out
  the weekly job
- `server.py` — the `DEPLOYED` branches in `status()`, `start_scrape()`,
  `_start_scrape_deployed()`, `scrape_status()`
- `lore.html`'s `initScrape()` — the `?ops=1` gate on the manual scrape UI
- `lore_engine/config.py` — `DEPLOYED`, `IS_LAMBDA`, `get_year_dir()`
- `requirements-worker.txt` / `requirements-scheduler.txt` — each Lambda's
  trimmed dependency set
