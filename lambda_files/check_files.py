import logging
import boto3
from botocore.exceptions import ClientError
import os
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def main():

  job_name = os.environ["JOB_NAME"]
  job_queue = os.environ["JOB_QUEUE"]
  job_definition = os.environ["JOB_DEFINITION"]
  s3_bucket_name = os.environ["S3_BUCKET_NAME"]
  input_prefix = 'input'

  batch = boto3.client('batch')
  s3 = boto3.client('s3')
  input_files = s3.list_objects(Bucket=s3_bucket_name, Prefix=input_prefix)['Contents']

  # there is at least 1 file
  if len(input_files) > 0:
    response = batch.submit_job(
      jobName= job_name,
      jobQueue= job_queue,
      jobDefinition= job_definition,
      containerOverrides={
          "environment": [
              {"name": "S3_BUCKET_NAME", "value": s3_bucket_name}
          ]
      })

    logger.info("AWS Batch Job ID is {}.".format(response['jobId']))

def handler(event, context):
  main()