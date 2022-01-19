FROM debian:buster-slim

ENV INSTALL_PATH /deepspeech
RUN mkdir -p $INSTALL_PATH

WORKDIR $INSTALL_PATH

# install build dependencies
RUN apt-get update && \
apt-get install -y \
wget \
unzip \
libcurl4-openssl-dev \
curl

# install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
&& unzip awscliv2.zip \
&& ./aws/install \
&& rm -f awscliv2.zip

# install python and its packages
RUN apt-get install -y python3
RUN apt-get install -y python3-pip
RUN python3 -m pip install boto3

# install sox in order to convert frequency of audios to 16000hz
RUN apt-get install -y sox

# install deeepspeech
RUN python3 -m pip install deepspeech

# copy inference and model files
COPY inference.py .
RUN mkdir model_files
RUN wget --directory-prefix=./model_files "https://github.com/mozilla/DeepSpeech/releases/download/v0.9.3/deepspeech-0.9.3-models.pbmm"
RUN wget --directory-prefix=./model_files "https://github.com/mozilla/DeepSpeech/releases/download/v0.9.3/deepspeech-0.9.3-models.scorer"

CMD ["python3", "inference.py"]