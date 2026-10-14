# Three separate credential paths, matching SCRAPING_ARCHITECTURE.md's "IAM
# is the part most likely to bite you" warning — keeping them least-privilege
# and distinct on purpose:
#   1. worker execution role   — assumed by the SQS-triggered scrape Lambda
#   2. scheduler execution role — assumed by the weekly EventBridge Lambda
#   3. lore-api IAM user        — static keys used by the Vercel API process
#      (Vercel functions can't assume a role the way Lambda can)

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# ── 1. Worker execution role ────────────────────────────────────────────────
# Needs: S3 object-level Get/Put/Head on the data bucket (NOT just the bucket
# ARN — a bucket-only ARN grants ListBucket but silently rejects PutObject,
# the exact gotcha SCRAPING_ARCHITECTURE.md calls out), DynamoDB Put/Get on
# the status table, and SQS receive/delete/get-attributes on the scrape queue.
resource "aws_iam_role" "worker" {
  name               = "${local.name_prefix}-worker"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "worker_logs" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "worker" {
  statement {
    sid = "DataObjectAccess"
    # s3:HeadObject and s3:GetObject are genuinely separate IAM actions
    # (confirmed via `aws iam simulate-principal-policy`, which refuses to
    # evaluate them together: "require different authorization information")
    # — an easy trap since the S3 API operation names line up 1:1 with these,
    # unlike some other services. Both are needed: HeadObject backs
    # is_cached_fresh()/get_last_scraped(), GetObject backs
    # get_cached_records()/get_raw_records().
    actions   = ["s3:GetObject", "s3:PutObject", "s3:HeadObject"]
    resources = ["${aws_s3_bucket.data.arn}/*"]
  }
  statement {
    # Same trap as the scheduler's FreshnessCheck (see that statement's
    # comment): without ListBucket, get_last_scraped()'s HeadObject on a
    # not-yet-scraped platform/year 403s instead of 404ing, which
    # get_last_scraped() doesn't catch — it only treats 404/NoSuchKey as "no
    # prior data", so every first-ever scrape of an incremental-merge
    # platform (hackernews/gamenews/gdelt/steam/appstore/googleplay) errored
    # out instead of falling back to a full fetch.
    sid       = "ListForCorrect404s"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn]
  }
  statement {
    sid       = "StatusTableAccess"
    actions   = ["dynamodb:PutItem", "dynamodb:GetItem"]
    resources = [aws_dynamodb_table.status.arn]
  }
  statement {
    sid       = "QueueConsume"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.scrape.arn]
  }
  statement {
    # Past-year reddit runs as a chain of parts (worker._process_reddit_history):
    # each part queues the next one itself, so the worker needs to send too.
    sid       = "QueueChainNextPart"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.scrape.arn]
  }
}

resource "aws_iam_role_policy" "worker" {
  name   = "${local.name_prefix}-worker"
  role   = aws_iam_role.worker.id
  policy = data.aws_iam_policy_document.worker.json
}

# ── 2. Scheduler execution role ─────────────────────────────────────────────
# Needs only: DynamoDB PutItem on the status table (the "queued" marker) and
# sqs:SendMessage — no S3 access at all. scheduler.py now only ever calls
# enqueue_missing_platforms(year, force=True), and force=True short-circuits
# past is_cached_fresh() (the HeadObject/ListBucket-needing freshness check)
# entirely — that path only existed for the old past-year backfill pass,
# which got removed (see scheduler.py's docstring: reddit's /hot/.rss listing
# can't meaningfully backfill past years no matter how long you wait, so a
# weekly backfill attempt was pure wasted worker time against it).
resource "aws_iam_role" "scheduler" {
  name               = "${local.name_prefix}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "scheduler_logs" {
  role       = aws_iam_role.scheduler.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    sid       = "StatusTableWrite"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.status.arn]
  }
  statement {
    sid       = "QueueProduce"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.scrape.arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "${local.name_prefix}-scheduler"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}

# ── 3. Vercel API user ──────────────────────────────────────────────────────
# The user only, no access key — Terraform state would hold the secret in
# plaintext forever if we generated the key here. Create the actual access
# key by hand (same pattern already used for the redtail-deploy admin user):
#   aws iam create-access-key --user-name redtail-lore-api --profile redtail-aws
# then put the two values straight into Vercel's env vars, never into a file.
resource "aws_iam_user" "lore_api" {
  name = "${local.name_prefix}-api"
  tags = local.tags
}

data "aws_iam_policy_document" "lore_api" {
  statement {
    sid       = "DataBucketAccess"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:HeadObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn, "${aws_s3_bucket.data.arn}/*"]
  }
  statement {
    sid = "AppTablesAccess"
    actions = [
      "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
      "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan",
    ]
    resources = [
      aws_dynamodb_table.status.arn,
      aws_dynamodb_table.waitlist.arn,
      aws_dynamodb_table.userdata.arn,
      aws_dynamodb_table.workspace.arn,
    ]
  }
  statement {
    sid       = "QueueProduce"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.scrape.arn]
  }
}

resource "aws_iam_user_policy" "lore_api" {
  name   = "${local.name_prefix}-api"
  user   = aws_iam_user.lore_api.name
  policy = data.aws_iam_policy_document.lore_api.json
}

# ── EventBridge Scheduler's own invoke role ─────────────────────────────────
# Separate from the scheduler Lambda's execution role above — this is the
# role EventBridge Scheduler itself assumes to call lambda:InvokeFunction,
# not the role the function runs as. Easy to conflate; they are not the same
# role.
data "aws_iam_policy_document" "scheduler_invoke_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler_invoke" {
  name               = "${local.name_prefix}-scheduler-invoke"
  assume_role_policy = data.aws_iam_policy_document.scheduler_invoke_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "scheduler_invoke" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.scheduler.arn]
  }
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  name   = "${local.name_prefix}-scheduler-invoke"
  role   = aws_iam_role.scheduler_invoke.id
  policy = data.aws_iam_policy_document.scheduler_invoke.json
}
