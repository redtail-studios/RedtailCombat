# Both functions are created with a placeholder deployment package (see
# lambda_stub/) — Terraform owns the function's config (role, env vars,
# timeout, trigger wiring), but the *code* is deployed the same way
# SCRAPING_ARCHITECTURE.md's runbook already does it (pip install the
# platform-specific wheels, zip, `aws lambda update-function-code`), just
# against these new function names. `ignore_changes` on filename/
# source_code_hash means re-running `terraform apply` after that real deploy
# won't revert it back to the stub.
#
# Runtime pinned to python3.13 — the newest one this AWS provider version
# (hashicorp/aws 5.100.0) actually validates. Git history references
# python3.14 ("Fix stale worker deploy: build for python3.14 to match Lambda
# runtime") from the old account's setup, but AWS Lambda doesn't expose that
# runtime yet as of this build; bump this once it's actually available and
# rebuild the worker/scheduler packages to match.

data "archive_file" "worker_stub" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_stub/worker"
  output_path = "${path.module}/.build/worker_stub.zip"
}

data "archive_file" "scheduler_stub" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_stub/scheduler"
  output_path = "${path.module}/.build/scheduler_stub.zip"
}

resource "aws_lambda_function" "worker" {
  function_name = "${local.name_prefix}-worker"
  role          = aws_iam_role.worker.arn
  handler       = "worker.handler" # SCRAPING_ARCHITECTURE.md gotcha: must exactly match, or every invocation fails at INIT silently
  runtime       = "python3.13"
  # 900s (Lambda's hard max) instead of 300s — reddit's scraper waits out a
  # ~60s rate-limit reset per subreddit, and with 20+ subreddits across
  # common + per-genre lists, a full run needs 20+ minutes of wall time.
  # 300s guaranteed a mid-run kill (confirmed via CloudWatch: every reddit
  # invocation hit exactly Duration=300000ms, Status=timeout) before it ever
  # got a chance to finish or fail cleanly. Must stay in lockstep with the
  # SQS queue's visibility_timeout_seconds (sqs.tf) — a mismatch there would
  # let SQS redeliver a message while the original invocation is still
  # running.
  timeout     = 900
  memory_size = 512

  filename         = data.archive_file.worker_stub.output_path
  source_code_hash = data.archive_file.worker_stub.output_base64sha256

  environment {
    variables = {
      AWS_BUCKET         = aws_s3_bucket.data.bucket
      LORE_S3_PREFIX     = var.s3_prefix
      LORE_DDB_STATUS_TABLE = aws_dynamodb_table.status.name
      LORE_SCRAPE_QUEUE_URL = aws_sqs_queue.scrape.url # chained reddit-history parts
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }

  tags = local.tags
}

resource "aws_lambda_event_source_mapping" "worker_sqs" {
  event_source_arn = aws_sqs_queue.scrape.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 1 # one message = one (year, platform) job, per SCRAPING_ARCHITECTURE.md
}

resource "aws_lambda_function" "scheduler" {
  function_name = "${local.name_prefix}-scheduler"
  role          = aws_iam_role.scheduler.arn
  handler       = "scheduler.handler"
  runtime       = "python3.13"
  timeout       = 60
  memory_size   = 128

  filename         = data.archive_file.scheduler_stub.output_path
  source_code_hash = data.archive_file.scheduler_stub.output_base64sha256

  environment {
    variables = {
      AWS_BUCKET            = aws_s3_bucket.data.bucket
      LORE_S3_PREFIX        = var.s3_prefix
      LORE_SCRAPE_QUEUE_URL = aws_sqs_queue.scrape.url
      LORE_DDB_STATUS_TABLE = aws_dynamodb_table.status.name
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }

  tags = local.tags
}

resource "aws_scheduler_schedule" "weekly_scrape" {
  name       = "${local.name_prefix}-weekly-scrape"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(7 days)"

  target {
    arn      = aws_lambda_function.scheduler.arn
    role_arn = aws_iam_role.scheduler_invoke.arn
  }
}
