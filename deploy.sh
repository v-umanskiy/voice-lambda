#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./deploy.sh
#   LAMBDA_NAME=hackathon_lambda ./deploy.sh

PROFILE="${AWS_PROFILE:-personal}"
REGION="${AWS_REGION:-eu-central-1}"
LAMBDA_NAME="${LAMBDA_NAME:-hackathon_lambda}"

ZIP_NAME="deploy.zip"
BUILD_DIR="build"
REQ_FILE="requirements.txt"

echo "========================================"
echo "Deploying Lambda"
echo "  Region:  $REGION"
echo "  Lambda:  $LAMBDA_NAME"
echo "  Profile: $PROFILE"
echo "========================================"

echo "==> Cleaning build artifacts"
rm -rf "$BUILD_DIR" "$ZIP_NAME"
mkdir -p "$BUILD_DIR"

echo "==> Installing dependencies"
pip install -r "$REQ_FILE" \
  --platform manylinux2014_x86_64 \
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
