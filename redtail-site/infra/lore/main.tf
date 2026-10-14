# Main Lore engine stack — S3 data bucket, SQS queue + DLQ, the worker +
# scheduler Lambdas, IAM roles, an EventBridge weekly schedule, and the four
# DynamoDB tables that replace storage.py's S3-blob status/waitlist/userdata/
# workspace paths (scraped platform data itself stays on S3 — see
# SCRAPING_ARCHITECTURE.md and the plan discussion for why).
#
# State lives in the bucket/table created by ../bootstrap — that stack must
# be applied first, exactly once per account.
#
# Usage:
#   cd redtail-site/infra/lore
#   terraform init
#   terraform plan  -var="aws_profile=redtail-aws"
#   terraform apply -var="aws_profile=redtail-aws"

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  backend "s3" {
    bucket         = "redtail-lore-tfstate-049584025697"
    key            = "lore/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "redtail-lore-tfstate-lock"
    encrypt        = true
    profile        = "redtail-aws" # backend config can't reference var.aws_profile — no interpolation allowed here
  }
}

variable "aws_profile" {
  description = "Named AWS CLI profile to use (see ~/.aws/credentials)."
  type        = string
  default     = "redtail-aws"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "environment" {
  description = "Deployment stage — isolates the S3 key prefix, DynamoDB table names, and resource names so a test stage can never collide with production. Matches storage.py's existing LORE_S3_PREFIX convention."
  type        = string
  default     = "prod"
}

variable "s3_prefix" {
  description = "Root S3 key prefix for scraped data (storage.py's LORE_S3_PREFIX)."
  type        = string
  default     = "lore"
}

provider "aws" {
  profile = var.aws_profile
  region  = var.aws_region
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  name_prefix = "redtail-lore-${var.environment}"
  tags = {
    Project     = "redtail-lore"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
