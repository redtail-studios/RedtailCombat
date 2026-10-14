# Everything Phase 5 (Vercel env var cutover) will need.

output "data_bucket" {
  value = aws_s3_bucket.data.bucket
}

output "scrape_queue_url" {
  value = aws_sqs_queue.scrape.url
}

output "scrape_dlq_url" {
  value = aws_sqs_queue.scrape_dlq.url
}

output "ddb_status_table" {
  value = aws_dynamodb_table.status.name
}

output "ddb_waitlist_table" {
  value = aws_dynamodb_table.waitlist.name
}

output "ddb_userdata_table" {
  value = aws_dynamodb_table.userdata.name
}

output "ddb_workspace_table" {
  value = aws_dynamodb_table.workspace.name
}

output "worker_function_name" {
  value = aws_lambda_function.worker.function_name
}

output "scheduler_function_name" {
  value = aws_lambda_function.scheduler.function_name
}

output "lore_api_iam_user" {
  description = "Create its access key by hand, not via Terraform — see iam.tf's comment on aws_iam_user.lore_api."
  value       = aws_iam_user.lore_api.name
}
