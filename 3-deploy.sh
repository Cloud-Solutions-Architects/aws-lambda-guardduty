#!/bin/bash
set -eo pipefail
source .var-file.sh

aws cloudformation package --template-file template.yml --s3-bucket $S3_BUCKET_NAME --output-template-file out.yml --region us-east-2
aws cloudformation deploy --template-file out.yml --stack-name fgt-guardduty-event --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides BucketFileName=$S3_BLOCKLIST_KEY BucketName=$S3_BUCKET_NAME --region us-east-2

rm -rf out.yml