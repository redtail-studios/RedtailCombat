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
   input needed — it always targets `storage.current_year()`), or someone
   hits `POST /api/lore/scrape` with a year via the ops UI.
2. Both paths call `storage.enqueue_missing_platforms(year, force=...)`. The
   scheduler passes `force=True` — the weekly cadence *is* the freshness
   mechanism now, so every platform gets re-enqueued regardless of TTL. The
   ops path passes `force=False`, preserving the original behavior: for each
   of the 18 platforms in `config.PLATFORM_IDS`, `storage.is_cached_fresh(year,
   platform)` (a cheap S3 `head_object`) decides whether that platform
   already has fresh data for that year (see §"Freshness / TTL" below).
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
  - `s3:PutObject`, `s3:GetObject`, `s3:HeadObject`, `s3:ListBucket` on the
    bucket — critically, on the **object-level ARN** (`arn:...:bucket/*`),
    not just the bucket-level ARN. A policy with only the bucket ARN grants
    `ListBucket`/`GetBucketVersioning` but silently rejects `PutObject`.
  - `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` on
    the queue.
  - `AWSLambdaBasicExecutionRole` for CloudWatch logs.
- **The scheduler Lambda** (`redtail-scrape-scheduler-role`) is narrower —
  it never reads scrape results or dequeues, so it only needs:
  - `s3:HeadObject`, `s3:PutObject` on the bucket's object ARN (freshness
    checks + status markers).
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
| *(weekly, automatic)* | — n/a — | EventBridge Scheduler → `scheduler.handler()` → `storage.enqueue_missing_platforms(year, force=True)`, no HTTP involved at all |
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

**Rebuild and redeploy the worker after a code change:**
```bash
rm -rf /tmp/lore-worker-build && mkdir -p /tmp/lore-worker-build
cp lore_engine/{worker,storage,config,manifest}.py /tmp/lore-worker-build/
cp -r lore_engine/scrapers /tmp/lore-worker-build/
pip install -r requirements-worker.txt \
  --platform manylinux2014_x86_64 --implementation cp --python-version 3.11 \
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
  --platform manylinux2014_x86_64 --implementation cp --python-version 3.11 \
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
cat /tmp/result.json   # {"year": 2026, "queued": [...]}
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
- `lore_engine/worker.py` — the SQS-triggered Lambda that does the actual scraping
- `lore_engine/scheduler.py` — the EventBridge-triggered Lambda that fans out
  the weekly job
- `server.py` — the `DEPLOYED` branches in `status()`, `start_scrape()`,
  `_start_scrape_deployed()`, `scrape_status()`
- `lore.html`'s `initScrape()` — the `?ops=1` gate on the manual scrape UI
- `lore_engine/config.py` — `DEPLOYED`, `IS_LAMBDA`, `get_year_dir()`
- `requirements-worker.txt` / `requirements-scheduler.txt` — each Lambda's
  trimmed dependency set
