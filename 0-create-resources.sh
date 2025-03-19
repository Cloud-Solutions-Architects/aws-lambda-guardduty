#!/bin/bash
source .var-file.sh

break > $S3_BLOCKLIST_KEY

aws s3 mb s3://${S3_BUCKET}
aws s3 cp $S3_BLOCKLIST_KEY s3://${S3_BUCKET}

rm -rf $S3_BLOCKLIST_KEY