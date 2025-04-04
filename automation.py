from argparse import ArgumentParser
from boto3.s3.transfer import S3Transfer

from dataclasses import dataclass
from dotenv import load_dotenv

import logging
import sys
import os
import boto3
import shutil

import jsonpickle

load_dotenv()
logFormatter = logging.Formatter(
    "%(asctime)s [%(threadName)-8.12s] [%(levelname)-4.5s]  %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)


@dataclass
class EnvironmentData():
    s3_bucket_name: str
    s3_file_name: str
    aws_region: str
    prefix: str


config: EnvironmentData = None


class S3BucketHelper(object):

    def __init__(self):
        self.client = boto3.client("s3")

    def set_bucket_policy(self, vpce_id: str):
        policy = {
            "Version": "2012-10-17",
            "Id": "Policy1415115909152",
            "Statement": [
                {
                    "Sid": "Access-to-specific-VPCE-only",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::%s/*" % config.s3_bucket_name,
                    "Condition": {
                        "StringEquals": {
                            "aws:sourceVpce": vpce_id
                        }
                    }
                }
            ]
        }
        logger.info(jsonpickle.encode(policy))
        self.client.put_bucket_policy(
            Bucket=config.s3_bucket_name, Policy=jsonpickle.encode(policy))
        logger.info("Adding policy to S3 bucket")

    def create_s3_bucket(self):
        logger.info("Creating S3 bucket.")
        if config.aws_region != "us-east-1":
            self.client.create_bucket(
                Bucket=config.s3_bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': config.aws_region}
            )
        else:
            self.client.create_bucket(Bucket=config.s3_bucket_name)

        open('tmp_file', 'a').close()
        transfer = S3Transfer(boto3.client('s3', config.aws_region))
        transfer.upload_file(
            'tmp_file', config.s3_bucket_name, config.s3_file_name)
        os.remove('tmp_file')
        logger.info("Creating S3 bucket - Done.")

    def delete_s3_bucket(self):
        logger.info("Deleting S3 bucket.")

        client = boto3.client('s3', config.aws_region)
        response = client.list_buckets()

        s3_bucket_exist = next(
            (x for x in response['Buckets'] if x['Name'] == config.s3_bucket_name), None)
        if (s3_bucket_exist):

            response = client.list_objects_v2(
                Bucket=config.s3_bucket_name, Prefix="")
            if 'Contents' in response:
                for object in response['Contents']:
                    logger.info("Deleting %s" % object['Key'])
                    client.delete_object(
                        Bucket=config.s3_bucket_name, Key=object['Key'])

            client.delete_bucket(
                Bucket=config.s3_bucket_name
            )
        else:
            logger.info("Bucket doesn't exist.")

        logger.info("Deleting S3 bucket - Done.")


class PipHelper(object):

    package_directory = "package"

    def delete_package_folder(self):
        if os.path.exists(self.package_directory):
            shutil.rmtree(self.package_directory)

    def create_package_folder(self):
        packages_path = "%s/package/python" % os.getcwd()
        requirement_path = "%s/function/requirements.txt" % os.getcwd()
        self.delete_package_folder()
        command = "pip3 install --target %s -r %s" % (
            packages_path, requirement_path)
        os.system(command)


class CloudFormationHelper(object):
    client = None
    template_out_file = "%s/out.yml" % os.getcwd()
    template_path_file = "%s/template.yml" % os.getcwd()

    def __init__(self):
        if os.path.exists(self.template_out_file):
            os.remove(self.template_out_file)

    def create_package(self):
        logger.info("Starting package process")
        command = "aws cloudformation package --template-file %s --s3-bucket %s --output-template-file %s --region %s"
        full_command = command % (
            self.template_path_file, config.s3_bucket_name, self.template_out_file, config.aws_region)
        logger.info("## Commnand: " + full_command)
        os.system(full_command)
        logger.info("Done - Starting package process")

    def create_stack(self):
        logger.info("Starting stack creation process")
        stack_name = "%s-FortiGate-GuardGuty-Finding-Security" % config.prefix
        command = "aws cloudformation deploy --template-file %s --stack-name %s --capabilities CAPABILITY_NAMED_IAM --parameter-overrides BucketFileName=%s BucketName=%s Prefix=%s --region %s"
        full_command = command % (self.template_out_file, stack_name, config.s3_file_name,
                                  config.s3_bucket_name, config.prefix, config.aws_region)
        logger.info("## Commnand: " + full_command)
        os.system(full_command)
        logger.info("Starting stack creation process - Done")

        if os.path.exists(self.template_out_file):
            os.remove(self.template_out_file)

    def delete_stack(self):
        logger.info("Starting stack deletion process")
        stack_name = "%s-FortiGate-GuardGuty-Finding-Security" % config.prefix

        command = "aws cloudformation delete-stack --stack-name %s" % stack_name
        logger.info("## Commnand: " + command)
        os.system(command)
        logger.info("Starting stack deletion process - Done")


class EC2Helper(object):
    def __init__(self):
        self.client = boto3.client("ec2")

    def create_vpce_s3(self, vpc_id, subnet_ids, security_group_ids):
        response = self.client.create_vpc_endpoint(
            VpcId=vpc_id,
            ServiceName='com.amazonaws.%s.s3' % config.aws_region,  # S3 service name
            SubnetIds=subnet_ids,
            SecurityGroupIds=security_group_ids,
            # PolicyDocument=policy_document, # Optional: Add a policy
            TagSpecifications=[
                {
                    'ResourceType': 'vpc-endpoint',
                    'Tags': [
                        {
                            'Key': 'Name', 'Value': 'vpc-endpoint-s3-interface-%s-fortinet-guardduty' % config.aws_region
                        },
                    ]
                },
            ],
            DryRun=False,  # Set to True for a dry run
            PrivateDnsEnabled=True,
            DnsOptions= { "PrivateDnsOnlyForInboundResolverEndpoint": False, "DnsRecordIpType": "ipv4"},
            VpcEndpointType='Interface'
        )
        
        # response = {'VpcEndpoint': {'VpcEndpointId': 'vpce-0aa88dfb8a072bb5b', 'VpcEndpointType': 'Interface', "DnsEntries": [{"DnsName": "*.vpce-0aa88dfb8a072bb5b-l0shckhq.s3.us-east-1.vpce.amazonaws.com","HostedZoneId": "Z7HUB22UULQXV"}]}}
        logger.debug(response)

        vpce_id = None
        if ('VpcEndpoint' in response):
            if ('VpcEndpointId' in response["VpcEndpoint"]):
                vpce_id = response["VpcEndpoint"]["VpcEndpointId"]
                s3Helper = S3BucketHelper()
                s3Helper.set_bucket_policy(vpce_id)

                for item in response["VpcEndpoint"]["DnsEntries"]:
                    if item["DnsName"].find(vpce_id) > 0:
                        logger.info("HTTP URL File:  https://bucket.%s/%s/%s" % (item["DnsName"][2:], config.s3_bucket_name, config.s3_file_name))
                
class Main(object):

    def bootstrap(self, args):

        logger.info('## EVENT: ' + jsonpickle.encode(config))

        if (args.step_id == 0):
            helper = S3BucketHelper()
            helper.create_s3_bucket()
        elif (args.step_id == 1):
            helper = PipHelper()
            helper.create_package_folder()

            helper2 = CloudFormationHelper()
            helper2.create_package()
            helper2.create_stack()
        elif (args.step_id == 2):
            helper = S3BucketHelper()
            helper.delete_s3_bucket()

            helper2 = PipHelper()
            helper2.delete_package_folder()

            helper3 = CloudFormationHelper()
            helper3.delete_stack()
        elif (args.step_id == 3):
            helpEC2 = EC2Helper()
            helpEC2.create_vpce_s3(args.vpc_id, args.subnet_ids, args.sg_ids)
        else:
            logger.error("Option not available.")
            pass


if __name__ == "__main__":
    logger.info("Starting automation script.")

    main_parser = ArgumentParser(
        description='Fortinet Cloud Solutions Team - GuardDuty Security Monitor', usage="python3 automation.py --step <Step ID>")
    main_parser.add_argument('--step', dest="step_id", type=int, required=True,
                             help="Which automation step to execute: 0 - for Create S3 Resource, 1 - For Deploy, 2 - For Cleaninig Up all creates resources, and 3 - For create the VPC Endpoint for EC2 private access.")
    main_parser.add_argument('--vpcId', dest="vpc_id", type=str,
                             required=False, help="VPC ID for the VPC Endpoint resource.")
    main_parser.add_argument('--subnetId', dest="subnet_ids", type=str, action="append",
                             required=False, help="List of subnet ids for the VPC Endpoint resource.")
    main_parser.add_argument('--sgId', dest="sg_ids", type=str, action="append",
                             required=False, help="List of securiry groups ids for the VPC Endpoint resource.")

    main_args = main_parser.parse_args()

    region = os.environ.get("AWS_REGION")
    prefix = os.environ.get("PREFIX")
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    file_name = os.environ.get("S3_BLOCKLIST_KEY_FILE")

    config = EnvironmentData(
        aws_region=region,
        prefix=prefix,
        s3_bucket_name="%s-%s" % (prefix, bucket_name),
        s3_file_name="%s-%s" % (prefix, file_name)
    )

    try:
        main = Main()
        main.bootstrap(main_args)
    except Exception as ex:
        logger.error(ex)
