FROM jupyter/datascience-notebook

LABEL org.opencontainers.image.source https://github.com/cal-itp/calitp-py

USER root
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt update \
    && apt install keychain \
    && apt install -y nodejs
USER $NB_UID

RUN curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-361.0.0-linux-x86_64.tar.gz \
    && tar -zxvf google-cloud-sdk-361.0.0-linux-x86_64.tar.gz \
    && ./google-cloud-sdk/install.sh

ADD _jupyterhub/requirements.txt /app/requirements.txt

RUN npm install -g --unsafe-perm=true --allow-root netlify-cli

RUN pip install -r /app/requirements.txt

RUN mkdir /opt/conda/share/jupyter/lab/settings/
COPY _jupyterhub/overrides.json /opt/conda/share/jupyter/lab/settings/overrides.json

COPY _jupyterhub/custom.sh /tmp/custom.sh
