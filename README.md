# calitp-py
Tools for accessing and analyzing cal-itp data

## Install

```
# Note that the tools to easily query the warehouse are being developed on a
# feature branch of siuba right now.
pip install git+https://github.com/machow/siuba.git@feat-bigquery

# Install calitp package
pip install git+https://github.com/cal-itp/calitp-py.git
```

## Configure

`calitp` uses the following environment variables:

* `CALITP_BQ_MAX_BYTES`
* `CALITP_BQ_LOCATION`
* `CALITP_USER`
* `AIRFLOW_ENV`
* `AIRFLOW__CORE__DAGS_FOLDER`
* `DAGS_FOLDER`
