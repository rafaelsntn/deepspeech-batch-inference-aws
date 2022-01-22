import boto3
import os
import numpy as np

s3_bucket_name = os.environ["S3_BUCKET_NAME"]
array_job_index = str(os.environ["AWS_BATCH_JOB_ARRAY_INDEX"]) if "AWS_BATCH_JOB_ARRAY_INDEX" in os.environ else "0"
input_prefix = 'input'
output_prefix = 'output'
processed_prefix = 'processed'
child_job_input_prefix = 'child_job_input'
mode_file = os.path.join('model_files','deepspeech-0.9.3-models.pbmm')
scorer_file = os.path.join('model_files','deepspeech-0.9.3-models.scorer')
tmp_folder = 'tmp'

s3 = boto3.client('s3')

# list of all audio files to transcribe
input_files = s3.list_objects(Bucket=s3_bucket_name, Prefix=input_prefix)['Contents']

# list of allowed audio files for this instance
child_job_input_file = os.path.join(os.sep, tmp_folder, array_job_index)
s3.download_file(s3_bucket_name, f'{child_job_input_prefix}/{array_job_index}', child_job_input_file)
allowed_input = np.loadtxt(child_job_input_file, dtype='str')

# iterate over all the files with "input" prefix
for f in input_files:
  # get the name of the audio file and download it
  input_key = f['Key'].split('/')[-1]
  if input_key not in allowed_input: continue

  input_file = os.path.join(os.sep, tmp_folder,input_key)
  output_key = input_key.split('.')[0]
  output_file = os.path.join(os.sep, tmp_folder,input_key.split('.')[0])
  s3.download_file(s3_bucket_name, f'{input_prefix}/{input_key}', input_file)

  # run speech to text inference
  os.system(f'''deepspeech --model {mode_file} --scorer {scorer_file} --audio {input_file} > {output_file}''')

  # upload the transcript and move input file from "input" folder to "processed" folder
  s3.upload_file(output_file, s3_bucket_name, f'{output_prefix}/{output_key}')
  s3.copy_object(Bucket=s3_bucket_name, CopySource=f'/{s3_bucket_name}/{input_prefix}/{input_key}', Key=f'{processed_prefix}/{input_key}')
  s3.delete_object(Bucket=s3_bucket_name, Key=f'{input_prefix}/{input_key}')
