# Data bucket — scraped platform records + status markers stay here (see
# SCRAPING_ARCHITECTURE.md). Status/waitlist/userdata/workspace are moving to
# DynamoDB (dynamodb.tf); this bucket keeps only the two things that are
# genuinely blob-shaped: data/<year>/<platform>.json and
# workspace/<kind>/<key>.<ext> binary assets (e.g. generated snapshot images).

resource "aws_s3_bucket" "data" {
  bucket = "${local.name_prefix}-data-${data.aws_caller_identity.current.account_id}"
  tags   = local.tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# No lifecycle expiry here on purpose — SCRAPING_ARCHITECTURE.md's freshness
# model is app-level (storage._is_fresh against LastModified + TTL), not a
# bucket lifecycle policy. Only the current calendar year is ever considered
# stale; past years are cached forever. Adding a bucket-level expiry would
# silently delete historical data the app assumes is permanent.
