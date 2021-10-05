FROM jupyter/datascience-notebook

ENV CALITP_SERVICE_KEY_PATH=/home/jovyan/warehouse_key.json

RUN pip install \
    git+https://github.com/machow/siuba.git@stable \
    calitp==0.0.6
