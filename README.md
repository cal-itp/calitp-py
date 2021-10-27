# calitp-py
Tools for accessing and analyzing cal-itp data

## Install

```
# Note that the tools to easily query the warehouse are being developed on a
# feature branch of siuba right now.
pip install git+https://github.com/machow/siuba.git@stable

# Install calitp package
pip install calitp

# Import and use cell magics
# depending on the calitp version, might need to pip uninstall calitp first 
pip install git+https://github.com/cal-itp/calitp-py@ipython-cell-magic

# To build within jupiterbooks documentation
jb build docs --all

# To use sql code magic within a codeblock in jupiterbooks
  ```{code-cell}
  %%sql
  SQL CODE

```

```
## Configure

`calitp` uses the following environment variables:

* `CALITP_BQ_MAX_BYTES`
* `CALITP_BQ_LOCATION`
* `CALITP_SERVICE_KEY_PATH` - an optional path to a google service key file.
* `CALITP_USER`
* `AIRFLOW_ENV`
* `AIRFLOW__CORE__DAGS_FOLDER`
* `DAGS_FOLDER`

### Configuration helper functions

| name | env variable | description |
| ---- | ------------ | ----------- |
| `is_development()` | `AIRFLOW_ENV` | E.g. changes project_id between staging and production. |
| `is_pipeline()` | `CALITP_USER` | Enables writing to warehouse. E.g. functions like `write_table()`. |
| `is_cloud()` | `CALITP_AUTH` | Toggles GCSFS authentication to "cloud" (vs "google_default"). |
