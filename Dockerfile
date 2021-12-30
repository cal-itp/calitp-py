FROM jupyter/datascience-notebook

RUN curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-361.0.0-linux-x86_64.tar.gz \
    && tar -zxvf google-cloud-sdk-361.0.0-linux-x86_64.tar.gz \
    && ./google-cloud-sdk/install.sh

RUN pip install \
    git+https://github.com/machow/siuba.git@stable \
    calitp==0.0.10 \
    intake==0.6.4 \
    intake-dcat==0.4.0 \
    intake-geopandas==0.3.0 \
    intake-parquet==0.2.3
