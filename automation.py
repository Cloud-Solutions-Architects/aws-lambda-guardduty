from argparse import ArgumentParser
from boto3.s3.transfer import S3Transfer

from dataclasses import dataclass
from dotenv import load_dotenv

from subprocess import check_output
import logging
import sys
import os
import subprocess
import boto3
import shutil

import jsonpickle

load_dotenv()
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
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
        self.s3_resource = boto3.resource("s3", region_name=config.aws_region)
    
    def create_s3_bucket(self):
        self.s3_resource.create_bucket(
            Bucket=config.s3_bucket_name
        )

        open('tmp_file', 'a').close()
        transfer = S3Transfer(boto3.client('s3', config.aws_region))
        transfer.upload_file('tmp_file', config.s3_bucket_name, config.s3_file_name)
        os.remove('tmp_file')


class PipHelper(object):

    package_directory = "package"

    def create_package_folder(self):
        if os.path.exists(self.package_directory):
            shutil.rmtree(self.package_directory)
        
        command = "pip3 install --target ./package/python -r ./function/requirements.txt"
        subprocess.run([command],check=True, capture_output=False, shell=True, cwd=os.getcwd())


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
        full_command = command % (self.template_path_file, config.s3_bucket_name, self.template_out_file, config.aws_region)
        logger.info("## Commnand: " + full_command)
        os.system(full_command)
        logger.info("Done - Starting package process")

    def create_stack(self):
        logger.info("Starting stack creation process")
        stack_name = "%s-FortiGate-GuardGuty-Finding-Security" % config.prefix
        command = "aws cloudformation deploy --template-file %s --stack-name %s --capabilities CAPABILITY_NAMED_IAM --parameter-overrides BucketFileName=%s BucketName=%s Prefix=%s --region %s"
        full_command = command % (self.template_out_file, stack_name, config.s3_file_name, config.s3_bucket_name,config.prefix, config.aws_region)
        logger.info("## Commnand: " + full_command)
        os.system(full_command)
        logger.info("Starting stack creation process - Done")


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
        else:
            logger.error("Option not available.")
            pass    
        

if __name__ == "__main__":
    logger.info("Starting automation script.")
    parser = ArgumentParser(description='Fortinet Cloud Solutions Team - GuardDuty Security Monitor')
    parser.add_argument('--step', dest="step_id", type=int, required=True, help="Which automation step to execute: 0 - for Create S3 Resource, 2  - For Deploy")
    args = parser.parse_args()

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

    # try:
    main = Main()
    main.bootstrap(args)
    # except Exception as ex:
    #     logger.error(ex)

