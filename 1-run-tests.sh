#!/bin/bash
set -eo pipefail
source .var-file.sh
cd ./function
python3 lambda_function.test.py
