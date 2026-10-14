# Four tables replacing storage.py's S3-blob paths for status/waitlist/
# userdata/workspace (see plan discussion — scraped platform data itself
# stays on S3; some platforms run 18k+ records, past DynamoDB's 400KB item
# cap). All on-demand billing — traffic here is low/spiky (dashboard polling,
# occasional signups), not worth capacity planning for.

# Replaces status/<year>/<platform>.json. Query by year alone returns every
# platform's status in one round trip instead of get_all_statuses()'s current
# 15 parallel S3 GETs.
resource "aws_dynamodb_table" "status" {
  name         = "${local.name_prefix}-status"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "year"
  range_key    = "platform"

  attribute {
    name = "year"
    type = "N"
  }
  attribute {
    name = "platform"
    type = "S"
  }

  tags = local.tags
}

# Replaces waitlist.json's unlocked read-modify-write array. email+submitted_at
# as a composite key (not just email) because add_waitlist_entry() never
# deduped — the same person can sign up more than once, and each signup is
# meant to be its own record, not an overwrite.
resource "aws_dynamodb_table" "waitlist" {
  name         = "${local.name_prefix}-waitlist"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "email"
  range_key    = "submitted_at"

  attribute {
    name = "email"
    type = "S"
  }
  attribute {
    name = "submitted_at"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true # real user-submitted data, not regenerable
  }

  tags = local.tags
}

# Replaces userdata/<username>.json — one item per user (reports + portfolio).
resource "aws_dynamodb_table" "userdata" {
  name         = "${local.name_prefix}-userdata"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "username"

  attribute {
    name = "username"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true # user-authored content, not regenerable
  }

  tags = local.tags
}

# Replaces workspace/<kind>/<key>.json (the JSON-document variant only — the
# workspace_get_bytes/put_bytes binary asset path, e.g. asset-image, stays on
# S3; DynamoDB items cap at 400KB and aren't meant for blobs).
resource "aws_dynamodb_table" "workspace" {
  name         = "${local.name_prefix}-workspace"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "kind"
  range_key    = "key"

  attribute {
    name = "kind"
    type = "S"
  }
  attribute {
    name = "key"
    type = "S"
  }

  tags = local.tags
}
