# FortiGate aws-lambda-guardduty - Parse GuardDuty Event (Python)

The project source includes function code and supporting resources:

- `function` - A Python function.
- `template.yml` - An AWS CloudFormation template that creates an application.
- `0-create-bucket.sh`, `2-build-layer.sh`, etc. - Shell scripts that use the AWS CLI to deploy and manage the application.

Use the following instructions to deploy this application.

# Requirements
- [Python 3.13](https://www.python.org/downloads/).
- [Pip](https://pypi.org/project/pip/).
- The Bash shell. For Linux and macOS, this is included by default. Maybe it's easier to install VS Code and use it's terminal.
- [The AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) v2.24.7 or newer.

# Setup
Download or clone this repository.

    git clone git@github.com:renesobral/aws-lambda-guardduty.git
    cd aws-lambda-guardduty

Edit the file `.var-file.sh` changing to your S3 Bucket name and the file name to save all IP Address to be blocked by FortiGate

To create a new bucket for deployment artifacts, run `0-create-bucket.sh`.

    ./0-create-bucket.sh

Example output:

    make_bucket: lambda-artifacts-a5e491dbb5b22e0d

To build a Lambda layer that contains the function's runtime dependencies, run `2-build-layer.sh`. Packaging dependencies in a layer reduces the size of the deployment package that you upload when you modify your code.

    ./2-build-layer.sh

# Deploy
To deploy the application, run `3-deploy.sh`.

    ./3-deploy.sh
    
Example output:

    Uploading to e678bc216e6a0d510d661ca9ae2fd941  9519118 / 9519118.0  (100.00%)
    Successfully packaged artifacts and wrote output template to file out.yml.
    Waiting for changeset to be created..
    Waiting for stack create/update to complete
    Successfully created/updated stack - fgt-guardduty-event

This script uses AWS CloudFormation to deploy:
- The Lambda functions and it's IAM role.
- The CloudWatch Filter and it's IAM role.


If the AWS CloudFormation stack that contains the resources already exists, the script updates it with any changes to the template or function code.

# Local Test
 Edit the file `lambda_function.test.py` on the line 20 to use as an input the event file with your testing payload.

 Then execute the script: 
```
./0-create-resources.sh
```

