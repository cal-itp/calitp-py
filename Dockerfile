FROM jupyter/datascience-notebook

RUN curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-361.0.0-linux-x86_64.tar.gz \
    && tar -zxvf google-cloud-sdk-361.0.0-linux-x86_64.tar.gz \
    && ./google-cloud-sdk/install.sh

ADD _jupyterhub/requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt
