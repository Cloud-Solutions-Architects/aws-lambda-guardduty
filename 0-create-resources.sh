#!/bin/bash
source .var-file.sh

echo "" > $S3_BLOCKLIST_KEY_FILE
aws s3 mb s3://${S3_BUCKET}

aws s3 cp $S3_BLOCKLIST_KEY_FILE s3://${S3_BUCKET}

rm -rf $S3_BLOCKLIST_KEY_FILE