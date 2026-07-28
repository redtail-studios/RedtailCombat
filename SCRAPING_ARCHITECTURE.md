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

Walking through one full cycle, in order:

1. Someone (or the frontend) calls `POST /api/lore/scrape` with a year.
   `server.py`'s `_start_scrape_deployed()` runs.
2. For each of the 15 platforms in `config.PLATFORM_IDS`, it calls
   `storage.is_cached_fresh(year, platform)` — a cheap S3 `head_object` that
   checks whether that platform already has fresh data for that year (see
   §"Freshness / TTL" below). Platforms that are already fresh are skipped
   entirely — nothing gets re-scraped or re-enqueued for them.
3. For every platform that's missing or stale, it writes a `"queued"` status
   marker (`storage.put_status`) and sends one SQS message
   (`storage.enqueue_scrape`) — message body is just `{"year": ..., "platform": ...}`.
   The API call returns immediately; it never waits for scraping itself.
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
| **S3** | The actual data store: scraped records (`<prefix>/data/<year>/<platform>.json`) and per-platform job status (`<prefix>/status/<year>/<platform>.json`) | The Lambda worker (`put_records`, `put_status`) and the API (`put_status` when enqueueing) | The API (status polling, manifest, report generation) and the worker (freshness isn't checked worker-side — see gotcha below) |
| **SQS** | The work queue — one message per `(year, platform)` job that needs scraping | The API (`enqueue_scrape`) | The Lambda's event source mapping (AWS-managed; not code you'll find in this repo) |
| **Lambda** | Runs the actual scraper code, off the request/response cycle entirely | — | Triggered by SQS |
| **IAM** | Two *separate* credential paths — see below | — | — |

**IAM is the part most likely to bite you**, because there are two
completely independent credential paths that both need to work:

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

## 3. Local vs. deployed, endpoint by endpoint

| Endpoint | Local (`DEPLOYED=False`) | Deployed (`DEPLOYED=True`) |
|---|---|---|
| `GET /api/lore/status` | Reads `lore_data/manifest.json` off disk | `storage.compute_manifest()` — live S3 listing |
| `POST /api/lore/scrape` | Spawns a background thread, scrapes all 15 platforms sequentially in-process | `_start_scrape_deployed()` — cache-check then SQS enqueue per platform |
| `GET /api/lore/scrape/status` | Reads the in-memory `_scrape` dict | `storage.scrape_status_snapshot()` — reads S3 status markers |
| `POST /api/lore/report` | `analysis.py` reads `lore_data/<year>/<platform>_data.json` off disk | `analysis.py` reads via `storage.get_cached_records()` |
| Scraper modules (`scrapers/*.py`) | Unchanged either way — `run()` doesn't know or care who's calling it | Unchanged either way |

## 4. Configuration reference

| Env var | Read by | Controls |
|---|---|---|
| `VERCEL` | API (`config.DEPLOYED`) | Set automatically by Vercel — this is *the* switch between local/deployed behavior |
| `AWS_LAMBDA_FUNCTION_NAME` | Worker (`config.IS_LAMBDA`) | Set automatically by the Lambda runtime — redirects `get_year_dir()` to `/tmp` so scrapers' local-disk write doesn't fail on Lambda's read-only filesystem |
| `AWS_BUCKET` | Both | Which S3 bucket everything lives in |
| `AWS_REGION` | Both | Region for S3/SQS clients (default `us-east-1`) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | API only | Vercel's static AWS credentials (the worker uses its execution role instead) |
| `LORE_SCRAPE_QUEUE_URL` | API only | The SQS queue to enqueue into — the worker never needs this, it's invoked *by* SQS, not polling it |
| `LORE_S3_PREFIX` | Both | Root S3 key prefix (default `"lore"`). **Override this for any test deployment** (e.g. `lore-test`) so test data can never collide with production's keyspace in the same bucket — this must match between the API's env and the worker Lambda's env, or they'll silently read/write different locations |
| `LORE_CACHE_TTL_SECONDS` | Both | Current-year freshness window (default 604800 = 7 days) |
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

**Trigger a scrape and watch it:**
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
- `lore_engine/storage.py` — all S3/SQS access
- `lore_engine/worker.py` — the Lambda entry point
- `server.py` — the `DEPLOYED` branches in `status()`, `start_scrape()`,
  `_start_scrape_deployed()`, `scrape_status()`
- `lore_engine/config.py` — `DEPLOYED`, `IS_LAMBDA`, `get_year_dir()`
- `requirements-worker.txt` — the worker's trimmed dependency set
