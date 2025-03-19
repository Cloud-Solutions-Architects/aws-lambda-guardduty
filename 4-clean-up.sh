#!/bin/bash
set -eo pipefail
source .var-file.sh

rm -rf package
rm -rf $S3_BLOCKLIST_KEY