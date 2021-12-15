# calitp-py
Tools for accessing and analyzing cal-itp data

## Install

```
# Note that the tools to easily query the warehouse are being developed on a
# feature branch of siuba right now.
pip install git+https://github.com/machow/siuba.git@stable

# Install calitp package
pip install calitp
```

## Test

Tests can be run using pytest:

```
pip install -r requirements.txt
pytest
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

## Release to PyPI

This package is automatically pushed to pypi upon release.

Releasing should follow this pattern:

* bump version number in `calitp/__init__.py`.
* create a pre-release, and verify the test release action worked.
* edit release, and uncheck the pre-release box.

## Release to Jupyterhub

This repo also handles pushing up a new jupyterhub image for calitp. See [this workflow file](https://github.com/cal-itp/calitp-py/blob/main/.github/workflows/docker.yml), which pushes on release.

The steps to update jupyterhub on the calitp cluster are as follows:

* create a calitp release
* check the corresponding action to ensure a new image was pushed
* follow the instructions in the data-infra docs on [updating the jupyterhub deploy](https://docs.calitp.org/data-infra/kubernetes/JupyterHub.html#updating).
