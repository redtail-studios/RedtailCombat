#!/usr/bin/env bash
# Builds and deploys the real lore_engine/scheduler.py to the scheduler
# Lambda — see deploy_worker.sh's header comment; same reasoning applies.
# Tiny package: only config.py + storage.py + python-dotenv, no scrapers.
set -euo pipefail

PROFILE="${AWS_PROFILE:-redtail-aws}"
FUNCTION_NAME="${SCHEDULER_FUNCTION_NAME:-redtail-lore-prod-scheduler}"
PY_VERSION="3.13"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"  # redtail-site/
ENGINE_DIR="$ROOT_DIR/lore_engine"
BUILD_DIR="$(mktemp -d /tmp/lore-scheduler-build.XXXXXX)"
ZIP_PATH="/tmp/lore-scheduler-$(date +%s).zip"

cleanup() { rm -rf "$BUILD_DIR"; }
trap cleanup EXIT

echo "==> Staging source into $BUILD_DIR"
cp "$ENGINE_DIR"/scheduler.py "$ENGINE_DIR"/storage.py "$ENGINE_DIR"/config.py "$BUILD_DIR/"

echo "==> Installing scheduler dependencies"
pip install -r "$ROOT_DIR/requirements-scheduler.txt" \
  --platform manylinux2014_x86_64 --implementation cp --python-version "$PY_VERSION" \
  --only-binary=:all: -t "$BUILD_DIR" --quiet

echo "==> Zipping"
rm -f "$ZIP_PATH"
( cd "$BUILD_DIR" && zip -r -q "$ZIP_PATH" . -x '*.pyc' '*/__pycache__/*' )

aws lambda update-function-code --function-name "$FUNCTION_NAME" \
  --zip-file "fileb://$ZIP_PATH" --profile "$PROFILE"
aws lambda wait function-updated --function-name "$FUNCTION_NAME" --profile "$PROFILE"
rm -f "$ZIP_PATH"
echo "==> Done: $FUNCTION_NAME is now running the real scheduler code"
