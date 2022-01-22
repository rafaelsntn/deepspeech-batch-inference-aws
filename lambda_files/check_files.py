import logging
import boto3
from botocore.exceptions import ClientError
import os
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def list_split(a, n):
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def main():

  job_name = os.environ["JOB_NAME"]
  job_queue = os.environ["JOB_QUEUE"]
  job_definition = os.environ["JOB_DEFINITION"]
  s3_bucket_name = os.environ["S3_BUCKET_NAME"]
  input_prefix = 'input'
  child_job_input_prefix = 'child_job_input'
  number_of_instances = 1

  batch = boto3.client('batch')
  s3 = boto3.client('s3')
  input_files = s3.list_objects(Bucket=s3_bucket_name, Prefix=input_prefix)

  # there is at least 1 file
  if 'Contents' not in input_files:
    logger.info("No input file was found. Upload the audio files (.wav) to bucket/input in S3.")
    
  else:
    # create files with balanced input keys to be read by child jobs
    input_keys = []
    for f in input_files['Contents']:
      input_keys.append(f['Key'].split('/')[-1])

    files_buckets = list_split(input_keys, number_of_instances)
    bucket_index = 0
    for b in files_buckets:
      with open(f'/tmp/{bucket_index}', 'w') as writer:
        writer.write('\n'.join(b))
      s3.upload_file(f'/tmp/{bucket_index}', s3_bucket_name, f'{child_job_input_prefix}/{bucket_index}')
      bucket_index+=1


    # submit the jobs
    array_properties = {}
    if number_of_instances > 1: array_properties['size'] = number_of_instances
    response = batch.submit_job(
      jobName= job_name,
      jobQueue= job_queue,
      jobDefinition= job_definition,
      arrayProperties=array_properties,
      containerOverrides={
          "environment": [
              {"name": "S3_BUCKET_NAME", "value": s3_bucket_name}
          ]
      })

    logger.info("AWS Batch Job ID is {}.".format(response['jobId']))

def handler(event, context):
  main()