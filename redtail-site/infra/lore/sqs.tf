# Scrape work queue — one message per (year, platform) job. The old setup
# had no documented DLQ, meaning a permanently-failing message (e.g. a
# scraper bug) would retry against visibility timeout indefinitely and never
# surface as distinguishable from "still working." Adding one here: after
# max_receive_count failed deliveries, SQS moves the message to the DLQ
# instead of retrying forever, and the DLQ's depth becomes a real alarm signal.

resource "aws_sqs_queue" "scrape_dlq" {
  name                      = "${local.name_prefix}-scrape-dlq"
  message_retention_seconds = 1209600 # 14 days — max, gives time to notice+debug
  tags                      = local.tags
}

resource "aws_sqs_queue" "scrape" {
  name                       = "${local.name_prefix}-scrape"
  visibility_timeout_seconds = 900 # must be >= the worker Lambda's timeout (lambda.tf)
  message_retention_seconds  = 345600 # 4 days

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.scrape_dlq.arn
    maxReceiveCount     = 3
  })

  tags = local.tags
}

resource "aws_sqs_queue_redrive_allow_policy" "scrape_dlq" {
  queue_url = aws_sqs_queue.scrape_dlq.id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.scrape.arn]
  })
}
