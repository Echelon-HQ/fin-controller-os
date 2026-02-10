#!/bin/bash
set -e

# Load env vars
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")
SNAPSHOT_NAME="fin-data-$TIMESTAMP.tar.gz"

echo "📦 Compressing financial data (excluding raw CSVs)..."
# We assume 'processed' and 'transactions.json' are what we need to sync
tar -czf $SNAPSHOT_NAME -C data processed transactions.json 2>/dev/null || echo "Warning: Some files missing, zipping what exists."

echo "☁️ Uploading to S3..."
aws s3 cp $SNAPSHOT_NAME s3://$S3_BUCKET_NAME/snapshots/latest_fin_data.tar.gz --endpoint-url=$S3_ENDPOINT
aws s3 cp $SNAPSHOT_NAME s3://$S3_BUCKET_NAME/snapshots/$SNAPSHOT_NAME --endpoint-url=$S3_ENDPOINT

rm $SNAPSHOT_NAME
echo "✅ Snapshot pushed successfully!"
