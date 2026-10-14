"""Placeholder — Terraform needs *some* deployment package to create the
function with. Replaced by the real lore_engine/worker.py via the existing
build-and-deploy runbook (SCRAPING_ARCHITECTURE.md §6) right after `apply`;
see lambda.tf's ignore_changes on filename/source_code_hash for why re-running
`terraform apply` afterward won't clobber that real deploy.
"""


def handler(event, context):
    print("worker stub — real code not deployed yet, see SCRAPING_ARCHITECTURE.md §6")
    return {"status": "stub"}
