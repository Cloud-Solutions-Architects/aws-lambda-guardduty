from argparse import ArgumentParser
from boto3.s3.transfer import S3Transfer
from botocore.config import Config

import random
import json
import logging
import sys
import os
import boto3
import shutil
import jsonpickle

logFormatter = logging.Formatter("%(asctime)s [%(threadName)-8.12s] [%(levelname)-4.5s]  %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)


class VPCEndpoint():
    def __init__(self, vpc_id, subnet_ids, security_group_ids):
        self.vpc_id: str = vpc_id
        self.subnet_ids: list[str] = subnet_ids
        self.security_group_ids: list[str] = security_group_ids
        self.vpce_id: str = ""


class EnvironmentData():
    def __init__(self, s3_bucket_name, s3_file_name, aws_region, prefix, endpoint):
        self.s3_bucket_name: str = "%s-%s" % (prefix, s3_bucket_name)
        self.s3_file_name: str = "%s-%s" % (prefix, s3_file_name)
        self.aws_region: str = aws_region
        self.prefix: str = prefix
        self.endpoint: VPCEndpoint = VPCEndpoint(**endpoint)


class SystemConfiguration():
    def __init__(self, environments):
        self.environments: list[EnvironmentData] = list()
        for item in environments:
            env = EnvironmentData(**item)
            self.environments.append(env)


system_config: SystemConfiguration = None
vpce_urls = []


class S3BucketHelper():

    def __init__(self):
        self.client = boto3.client("s3")

    def set_bucket_policy(self, config: EnvironmentData):
        policy = {
            "Version": "2012-10-17",
            "Id": "Policy14%s" % random.randint(100001, 1000000),
            "Statement": [
                {
                    "Sid": "Access-to-specific-VPCE-only",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::%s/*" % config.s3_bucket_name,
                    "Condition": {
                        "StringEquals": {
                            "aws:sourceVpce": config.endpoint.vpce_id
                        }
                    }
                }
            ]
        }
        logger.info(jsonpickle.encode(policy))
        self.client.put_bucket_policy(
            Bucket=config.s3_bucket_name, Policy=jsonpickle.encode(policy))
        logger.info("Adding policy to S3 bucket")

    def create_s3_bucket(self, config: EnvironmentData):
        logger.info("Creating S3 bucket: %s, region: %s." % (config.s3_bucket_name, config.aws_region))
        try:
            if config.aws_region != "us-east-1":
                self.client.create_bucket(
                    Bucket=config.s3_bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': config.aws_region}
                )
            else:
                self.client.create_bucket(Bucket=config.s3_bucket_name)

        except  self.client.exceptions.BucketAlreadyOwnedByYou as err:
            logger.error(err)

        open('tmp_file', 'a').close()
        transfer = S3Transfer(boto3.client('s3', config.aws_region))
        transfer.upload_file(
            'tmp_file', config.s3_bucket_name, config.s3_file_name)
        os.remove('tmp_file')
        logger.info("Creating S3 bucket - Done.")

    def delete_s3_bucket(self, config: EnvironmentData):
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

    def create_package(self, config: EnvironmentData):
        logger.info("Starting package process")
        command = "aws cloudformation package --template-file %s --s3-bucket %s --output-template-file %s --region %s"
        full_command = command % (
            self.template_path_file, config.s3_bucket_name, self.template_out_file, config.aws_region)
        logger.info("## Commnand: " + full_command)
        os.system(full_command)
        logger.info("Done - Starting package process")

    def create_stack(self, config: EnvironmentData):
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

    def delete_stack(self, config: EnvironmentData):
        logger.info("Starting stack deletion process")
        stack_name = "%s-FortiGate-GuardGuty-Finding-Security" % config.prefix

        command = "aws cloudformation delete-stack --stack-name %s" % stack_name
        logger.info("## Commnand: " + command)
        os.system(command)
        logger.info("Starting stack deletion process - Done")


class EC2Helper(object):

    def create_vpce_s3(self, config: EnvironmentData):
        boto_client_config = Config(region_name=config.aws_region)
        self.client = boto3.client("ec2", config=boto_client_config)
        response = self.client.create_vpc_endpoint(
            VpcId=config.endpoint.vpc_id,
            ServiceName='com.amazonaws.%s.s3' % config.aws_region,  # S3 service name
            SubnetIds=config.endpoint.subnet_ids,
            SecurityGroupIds=config.endpoint.security_group_ids,
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
            DnsOptions={
                "PrivateDnsOnlyForInboundResolverEndpoint": False, "DnsRecordIpType": "ipv4"},
            VpcEndpointType='Interface'
        )

        # response = {'VpcEndpoint': {'VpcEndpointId': 'vpce-0aa88dfb8a072bb5b', 'VpcEndpointType': 'Interface', "DnsEntries": [{"DnsName": "*.vpce-0aa88dfb8a072bb5b-l0shckhq.s3.us-east-1.vpce.amazonaws.com","HostedZoneId": "Z7HUB22UULQXV"}]}}
        logger.debug(response)

        if ('VpcEndpoint' in response):
            if ('VpcEndpointId' in response["VpcEndpoint"]):
                config.endpoint.vpce_id = response["VpcEndpoint"]["VpcEndpointId"]
                s3Helper = S3BucketHelper()
                s3Helper.set_bucket_policy(config)

                for item in response["VpcEndpoint"]["DnsEntries"]:
                    if item["DnsName"].find(config.endpoint.vpce_id) > 0:
                        url = "HTTP URL File:  https://bucket.%s/%s/%s" % (item["DnsName"][2:], config.s3_bucket_name, config.s3_file_name)
                        vpce_urls.append(url)
                        return

    def delete_vpce_s3(self, config: EnvironmentData):
        boto_client_config = Config(region_name=config.aws_region)
        self.client = boto3.client("ec2", config=boto_client_config)


class Main(object):

    def bootstrap(self, args):

        logger.info('## CONFIG_FILE: ' + jsonpickle.encode(system_config))

        if (args.step_id == 0):
            s3_client = S3BucketHelper()
            for item in system_config.environments:
                s3_client.create_s3_bucket(item)

        elif (args.step_id == 1):
            helper = PipHelper()
            helper.create_package_folder()

            helper2 = CloudFormationHelper()
            for item in system_config.environments:
                helper2.create_package(item)
                helper2.create_stack(item)

        elif (args.step_id == 2):

            helpEC2 = EC2Helper()
            for item in system_config.environments:
                helpEC2.create_vpce_s3(item)

            logger.info("#######################################################")
            logger.info("################### VPC Enpoint URLs ##################")
            for item in vpce_urls:
                logger.info(item)
            logger.info("#######################################################")
            logger.info("#######################################################")

        elif (args.step_id == 3):

            s3_client = S3BucketHelper()
            for item in system_config.environments:
                s3_client.delete_s3_bucket(item)

            helper2 = PipHelper()
            helper2.delete_package_folder()

            helper3 = CloudFormationHelper()
            for item in system_config.environments:
                helper3.delete_stack(item)
        else:
            logger.error("Option not available.")
            pass


if __name__ == "__main__":
    logger.debug("Starting automation script.")

    main_parser = ArgumentParser(
        description='Fortinet Cloud Solutions Team - GuardDuty Security Monitor', usage="python3 automation.py --step <Step ID> --config <config file path>")
    main_parser.add_argument('--step', dest="step_id", type=int, required=True,
                             help="Which automation step to execute: 0 - for Create S3 Resource, 1 - For Deploy, 2 - For create the VPC Endpoint for EC2 private access.")
    main_parser.add_argument('--config', dest="config_file", type=str, required=True,
                             help="Configuration file.")
    main_args = main_parser.parse_args()

    try:
        with open(main_args.config_file, 'r') as fr:
            json_value = json.load(fr)
            system_config = SystemConfiguration(**json_value)

            logger.info(system_config)

        main = Main()
        main.bootstrap(main_args)
    except Exception as ex:
        logger.error(ex)
