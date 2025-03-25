# FortiGate aws-lambda-guardduty - Parse GuardDuty Event

![Overall](./images/Overall.png)


The project source includes function code and supporting resources:

- `function` - A Python function.
- `template.yml` - An AWS CloudFormation template that creates and configure this application.
- `0-create-resources.sh`, `2-build-layer.sh`, etc. - Shell scripts that use the AWS CLI to deploy and manage the application.

Use the following instructions to deploy this application.

## Requirements
- [Python 3.13](https://www.python.org/downloads/).
- The Bash shell. For Linux and macOS, this is included by default. In Windows 10, you can install the [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/install-win10) to get a Windows-integrated version of Ubuntu and Bash.
- [The AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) v2.24.7 or newer.

### Python Lib Requirements
- jsonpickle 4.0.2
- aws-xray-sdk 2.14.0
- jmespath 1.0.1
- boto3

## Resources
Upon executing the #3 script, a CloudFormation Stack will be created, provisioning the following resources:
 * EventBridge Rule: A rule that acts as a trigger for the Serverless function, filtering only GuardDuty Findings events.
 * IAM Role and Policy: Automatically configured roles and policies required for the Serverless function and the EventBridge Rule.
 * Lambda Function (Serverless): The automation script packages and uploads all necessary files to an S3 bucket, then creates a new Lambda function.

In total, eight resources are deployed, including rules, IAM roles, and the Lambda function.

### AIM Role and Policy
The CloudFormation Template (CFT) will create specific IAM roles and policies, explicitly defined in the `template.yml` file. Below are the scope and permissions assigned by the CFT:

#### Lambda Function

The function will have restricted access to a specific S3 bucket and the necessary permissions to execute. These include:
- AWSLambdaBasicExecutionRole
- AWSLambda_ReadOnlyAccess
- AWSXrayWriteOnlyAccess
- s3:ListAllMyBuckets
- s3:GetObject
- s3:PutObject

#### Event Rule

This rule will grant permission to events.amazonaws.com and allow it to invoke only our serverless function. The assigned permissions are:
- sts:AssumeRole
- lambda:InvokeFunction



## Setup
Download or clone this repository.

    git clone git@github.com:renesobral/aws-lambda-guardduty.git
    cd aws-lambda-guardduty

Edit the file `.var-file.sh` changing to your S3 Bucket name, file name inside the S3 Bucket that will have a list of IP addresss, and the region the serverless function will run.

To create a new bucket for deployment artifacts, run `0-create-resources.sh`.

    ./0-create-resources.sh

Example output:

    make_bucket: lambda-artifacts-a5e491dbb5b22e0d

To build a Lambda layer that contains the function's runtime dependencies, run `2-build-layer.sh`. Packaging dependencies in a layer reduces the size of the deployment package that you upload when you modify your code.

    ./2-build-layer.sh

### Automation Deploy
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

## Local Test
 Edit the file `lambda_function.test.py` on the line 20 to use as an input the event file with your testing payload.

 Then execute the script, if you haven't already: 
```
./0-create-resources.sh
```
Next, you can execute the file `1-run-tests.sh`

> Make sure you have valid credentials to your AWS environment.

# FortiGate Configuration
> TDB