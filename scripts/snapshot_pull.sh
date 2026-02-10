#!/bin/bash
set -e

# Load env vars
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

echo "⬇️ Downloading latest financial snapshot..."
aws s3 cp s3://$S3_BUCKET_NAME/snapshots/latest_fin_data.tar.gz temp_snapshot.tar.gz --endpoint-url=$S3_ENDPOINT

echo "📂 Extracting data..."
mkdir -p data
tar -xzf temp_snapshot.tar.gz -C data

rm temp_snapshot.tar.gz
echo "✅ Data synced! You are ready to go offline."
