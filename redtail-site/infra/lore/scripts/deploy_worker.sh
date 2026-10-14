#!/usr/bin/env bash
# Builds and deploys the real lore_engine/worker.py to the worker Lambda
# Terraform created with a placeholder stub (see ../lambda.tf's
# ignore_changes on filename/source_code_hash — this script's deploys are
# exactly what that's there to not get reverted by a future `terraform apply`).
#
# Adapted from SCRAPING_ARCHITECTURE.md §6's runbook: same shape, pointed at
# the new account's function name and python3.13 (not 3.14 — see lambda.tf's
# comment on why).
set -euo pipefail

PROFILE="${AWS_PROFILE:-redtail-aws}"
FUNCTION_NAME="${WORKER_FUNCTION_NAME:-redtail-lore-prod-worker}"
PY_VERSION="3.13"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"  # redtail-site/
ENGINE_DIR="$ROOT_DIR/lore_engine"
BUILD_DIR="$(mktemp -d /tmp/lore-worker-build.XXXXXX)"
ZIP_PATH="/tmp/lore-worker-$(date +%s).zip"

cleanup() { rm -rf "$BUILD_DIR"; }
trap cleanup EXIT

echo "==> Staging source into $BUILD_DIR"
cp "$ENGINE_DIR"/worker.py "$ENGINE_DIR"/storage.py "$ENGINE_DIR"/config.py "$BUILD_DIR/"
cp -r "$ENGINE_DIR"/scrapers "$BUILD_DIR/"

echo "==> Installing worker dependencies (manylinux2014_x86_64, cp$PY_VERSION)"
pip install -r "$ROOT_DIR/requirements-worker.txt" \
  --platform manylinux2014_x86_64 --implementation cp --python-version "$PY_VERSION" \
  --only-binary=:all: -t "$BUILD_DIR" --quiet

echo "==> Zipping"
rm -f "$ZIP_PATH"  # zip merges into an existing archive instead of overwriting — always start clean
( cd "$BUILD_DIR" && zip -r -q "$ZIP_PATH" . -x '*.pyc' '*/__pycache__/*' )

SIZE_MB=$(( $(stat -f%z "$ZIP_PATH" 2>/dev/null || stat -c%s "$ZIP_PATH") / 1024 / 1024 ))
echo "==> Package size: ${SIZE_MB}MB compressed"

if [ "$SIZE_MB" -ge 50 ]; then
  echo "==> Over 50MB — staging through S3 (direct --zip-file upload isn't allowed past that size)"
  STAGING_BUCKET=$(terraform -chdir="$(dirname "${BASH_SOURCE[0]}")/.." output -raw data_bucket)
  STAGING_KEY="_lambda-deploys/worker-$(date +%s).zip"
  aws s3 cp "$ZIP_PATH" "s3://$STAGING_BUCKET/$STAGING_KEY" --profile "$PROFILE"
  aws lambda update-function-code --function-name "$FUNCTION_NAME" \
    --s3-bucket "$STAGING_BUCKET" --s3-key "$STAGING_KEY" --profile "$PROFILE"
  aws s3 rm "s3://$STAGING_BUCKET/$STAGING_KEY" --profile "$PROFILE"
else
  aws lambda update-function-code --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_PATH" --profile "$PROFILE"
fi

echo "==> Waiting for update to finish"
aws lambda wait function-updated --function-name "$FUNCTION_NAME" --profile "$PROFILE"
rm -f "$ZIP_PATH"
echo "==> Done: $FUNCTION_NAME is now running the real worker code"
