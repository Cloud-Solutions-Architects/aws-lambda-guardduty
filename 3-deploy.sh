#!/bin/bash
set -eo pipefail
source .var-file.sh

aws cloudformation package --template-file template.yml --s3-bucket $S3_BUCKET --output-template-file out.yml --region $AWS_REGION
aws cloudformation deploy --template-file out.yml --stack-name $PREFIX-FortiGate-GuardGuty-Finding-Security --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides BucketFileName=$S3_BLOCKLIST_KEY BucketName=$S3_BUCKET Prefix=$PREFIX --region $AWS_REGION

rm -rf out.yml