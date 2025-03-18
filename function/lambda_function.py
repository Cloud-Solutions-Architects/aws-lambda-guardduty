from dataclasses import dataclass
import os
import logging
import jsonpickle
import boto3
import jmespath

from aws_xray_sdk.core import patch_all

logger = logging.getLogger()
logger.setLevel(logging.INFO)
patch_all()

BUCKET_NAME = os.environ["S3_BUCKET"]
BUCKET_FILE = os.environ["S3_BLOCKLIST_KEY"]

def lambda_handler(event, context):
    logger.info('## EVENT: ' + jsonpickle.encode(event))

    logger.info("Lambda function started, parsing events")  

    notifications = NotificationHelper.parser(event)
    all_ip_addresses = list()

    for item in notifications:
        if item.ip not in all_ip_addresses:
            logger.info("Processing event id: %s, IP: %s" % (item.id, item.ip))
            all_ip_addresses.append(item.ip)

    if ( len(all_ip_addresses) > 0):
        logger.info("Appending to S3 bucket")

        s3helper = S3BucketHelper(BUCKET_FILE, BUCKET_NAME)
        s3helper.add_list_of_addresses(all_ip_addresses)
        logger.info("Appending S3 bucket IP List - Done")

    return { "statusCode": 200, "body": '' }


class S3BucketHelper(object):
    def __init__(self, file, bucket):
        self.file = file
        self.bucket = bucket
        self.client = boto3.client('s3')
        
    def add_list_of_addresses(self, new_ip_address: list):
        
        should_upload = False
        existent_file = self._download_file()
        all_ip_addresses = []

        if(existent_file):
            it = existent_file['Body'].iter_lines()
            
            for i, line in enumerate(it):
                if (len(line.decode('utf-8'))> 0):
                    all_ip_addresses.append(line.decode('utf-8'))

        for ip in new_ip_address:
            if(ip not in all_ip_addresses):
                all_ip_addresses.append(ip)
                should_upload = True    
    
        if (should_upload):
            self._upload_file(all_ip_addresses)
    
    def _upload_file(self, data: list) -> None:
         self.client.put_object(Body='\n'.join(data), Bucket=self.bucket, Key=self.file)

    def _download_file(self):
        return self.client.get_object(Bucket=self.bucket, Key=self.file)
            

@dataclass
class EventNotification():

    id: str
    # serviceName: str
    ip: str
    direction: str
    # threatListName: list

class NotificationHelper():

    @staticmethod
    def parser(event_json) -> list[EventNotification]:

        query_ip = {
            "networkConnectionAction":"detail.service.action.networkConnectionAction.remoteIpDetails.ipAddressV4",
            "kubernetesApiCallAction":"detail.service.action.kubernetesApiCallAction.remoteIpDetails.ipAddressV4",
            "awsApiCallAction":"detail.service.action.awsApiCallAction.remoteIpDetails.ipAddressV4",
            "rdsLoginAttemptAction":"detail.service.action.rdsLoginAttemptAction.remoteIpDetails.ipAddressV4"
        }

        listToReturn: list[EventNotification] = list()
        
        # query = """{ 
        #     last_seen: detail.service.eventLastSeen,
        #     service_name: detail.service.serviceName,
        #     threat_list_name:  detail.service.svidence.threatIntelligenceDetails[].threatListName
        # }"""
        if (type(event_json) == dict):
            event_json = [event_json]
                
        for evt in event_json:
            ip = None
            direction = None

            for key, item in query_ip.items():
                ip = jmespath.search(item, evt)
                if(ip):
                    direction_expression = "Service.Action.%s.ConnectionDirection" % key
                    direction = jmespath.search(direction_expression, evt)
                    break

            if(not(ip) and (not(direction) or direction != "OUTBOUND")):
                logger.info("Ignoring event id: %s" %  evt["id"])
                continue

            # result = jmespath.search(query, evt)
            
            # newEvent: EventNotification = EventNotification(evt["id"], result["service_name"], ip, direction, result["threat_list_name"])
            newEvent: EventNotification = EventNotification(evt["id"], ip, direction)
            listToReturn.append(newEvent)

        return listToReturn

class Helper(object):
    @staticmethod
    def is_bucket_valid():
        
        logger.info("Validating Bucket data...")
        if not(os.environ["S3_BLOCKLIST_KEY"] or os.environ["S3_BUCKET"]):
            logger.info("Bucket name or IP List file not found on the environment variables.")
            return False
        
        s3 = boto3.resource('s3')
        bucket_exist = s3.Bucket(BUCKET_NAME) in s3.buckets.all()
        if not(bucket_exist):
            logger.info("Bucket %s doesn't exist." % BUCKET_NAME)
            return False

        s3Client = boto3.client('s3')
        try:        
            s3Client.get_object(Bucket=BUCKET_NAME, Key=BUCKET_FILE)
        except s3Client.exceptions.NoSuchKey as e:
            logger.info("IP File doesn't exist, the system is creating a new one.")
            s3Client.put_object(Body = "", Bucket=BUCKET_NAME, Key=BUCKET_FILE)
        
        return True
    
        

