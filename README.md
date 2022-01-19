# Deepspeech batch inference via CDK deployment in AWS

This project is intended to give an alternative implementation of a Speech to Text solution in the cloud using [Deepspeech](https://github.com/mozilla/DeepSpeech). The cloud providers do a great job building amazing Speech to Text solutions, but may be some reasons for building a custom solution instead of using an off-the-shelf one:
- You may need a more fine tuned model.
- The cloud provider API can be much more expensive than the use of some open sources alternatives, depending on the volume of data to be processed.

## Solution archictecture

TODO

## AWS deployment

### To deploy and run the solution, you need access to:
- An AWS account.
- A terminal with AWS Command Line Interface (CLI), CDK, Docker, git, and Python installed.

### Open a terminal and follow these steps:
1. Clone the GitHub repo <br />
`git clone https://github.com/rafaelsntn/deepspeech-batch-inference-aws`
2. Create a virtual environment: <br />
`python -m venv .venv`
3. Activate the virtual environment: <br />
In Linux: <br />
`source .venv/bin/activate` <br />
In Windows: <br />
`.venv\Scripts\activate.bat`
4. Once the virtualenv is activated, you can install the required dependencies: <br />
`pip install -r requirements.txt`
5. Deploy to AWS: <br />
`cdk deploy`

## Running inference
After deployment, you will see a new bucket in S3. To run the batch inference, you just need to upload the audio files with the extension ".wav". The file keys in the bucket will follow the pattern:
- {bucket-name}/input/{audio-file-name.wav} <br />
    Audio files that will be transcribed by Deepspeech.
- {bucket-name}/output/{audio-file-name} <br />
    After processing the audio file, the transcribed text will be saved here.
- {bucket-name}/processed/{audio-file.wav} <br />
    Move the processed files from input to processed.

The deployment will schedule a cronjob via EventBridge at 1 a.m. (GMT) to run the Lambda function that submits the batch job. If there isn't no input files to be processed, the Lambda function exits without submitting the job, saving costs of EC2 instances. Alternatively, you can run the lambda function directly in the AWS console.

## License

This solution is licensed under the MIT-0 License. See the LICENSE file.