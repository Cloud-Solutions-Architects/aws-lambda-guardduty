#!/bin/bash
set -eo pipefail
source .var-file.sh

aws cloudformation package --template-file template.yml --s3-bucket $S3_BUCKET_NAME --output-template-file out.yml --region $AWS_REGION
aws cloudformation deploy --template-file out.yml --stack-name FortiGate-GuardGuty-Finding-Security --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides BucketFileName=$S3_BLOCKLIST_KEY BucketName=$S3_BUCKET_NAME --region $AWS_REGION

rm -rf out.yml