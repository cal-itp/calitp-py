FROM jupyter/datascience-notebook

RUN pip install \
    git+https://github.com/machow/siuba.git@stable \
    calitp==0.0.4
