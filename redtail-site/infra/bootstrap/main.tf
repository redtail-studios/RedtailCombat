# Bootstrap stack — creates the S3 bucket + DynamoDB table that the *real*
# Terraform stack (../lore) uses as its remote state backend.
#
# This has to stay a separate, local-state config: you can't point Terraform
# at an S3 backend that doesn't exist yet. Run this once per AWS account,
# then never touch it again unless the state bucket/lock table themselves
# need to change.
#
# Usage:
#   cd redtail-site/infra/bootstrap
#   terraform init
#   terraform apply -var="aws_profile=redtail-aws"

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "aws_profile" {
  description = "Named AWS CLI profile to use (see ~/.aws/credentials)."
  type        = string
  default     = "redtail-aws"
}

variable "aws_region" {
  description = "Region for the state bucket + lock table."
  type        = string
  default     = "us-east-1"
}

provider "aws" {
  profile = var.aws_profile
  region  = var.aws_region
}

data "aws_caller_identity" "current" {}

# Bucket name must be globally unique across all of AWS — suffix with the
# account ID rather than a random string so it's reproducible and traceable
# to this account at a glance.
resource "aws_s3_bucket" "tfstate" {
  bucket = "redtail-lore-tfstate-${data.aws_caller_identity.current.account_id}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# State-locking table for the main stack's S3 backend.
resource "aws_dynamodb_table" "tflock" {
  name         = "redtail-lore-tfstate-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  lifecycle {
    prevent_destroy = true
  }
}

output "state_bucket" {
  value = aws_s3_bucket.tfstate.bucket
}

output "lock_table" {
  value = aws_dynamodb_table.tflock.name
}

output "account_id" {
  value = data.aws_caller_identity.current.account_id
}
