#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./deploy.sh
#   LAMBDA_NAME=hackathon_lambda ./deploy.sh

PROFILE="${AWS_PROFILE:-personal}"
REGION="${AWS_REGION:-eu-central-1}"
LAMBDA_NAME="${LAMBDA_NAME:-hackathon_lambda}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

ZIP_NAME="deploy.zip"
BUILD_DIR="build"
REQ_FILE="requirements.txt"

echo "========================================"
echo "Deploying Lambda"
echo "  Region:  $REGION"
echo "  Lambda:  $LAMBDA_NAME"
echo "  Profile: $PROFILE"
echo "  Python:  $PYTHON_BIN"
echo "========================================"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: $PYTHON_BIN is not installed."
  echo "Install Python 3.12 or run with PYTHON_BIN=<path-to-python3.12>."
  exit 1
fi

echo "==> Cleaning build artifacts"
rm -rf "$BUILD_DIR" "$ZIP_NAME"
mkdir -p "$BUILD_DIR"

echo "==> Installing dependencies"
"$PYTHON_BIN" -m pip install -r "$REQ_FILE" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --abi cp312 \
  --only-binary=:all: \
  --target "$BUILD_DIR"

echo "==> Copying source files"
cp -r *.py "$BUILD_DIR"/

echo "==> Creating deployment zip"
(
  cd "$BUILD_DIR"
  zip -r "../$ZIP_NAME" .
)

echo "==> Uploading to AWS Lambda"
aws lambda update-function-code \
  --function-name "$LAMBDA_NAME" \
  --zip-file "fileb://$ZIP_NAME" \
  --region "$REGION" \
  --profile "$PROFILE" \
  --no-cli-pager \
  --query 'FunctionArn' \
  --output text

echo "✅ Deployment complete."
