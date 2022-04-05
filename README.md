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

## Release Package to PyPI

This package is automatically pushed to pypi upon release.

Releasing should follow this pattern:

* bump version number in `calitp/__init__.py`.
* create a pre-release, and verify the test release action worked. The tag should be `v{VERSION}`, e.g. `v0.0.1`.
* edit release, and uncheck the pre-release box.

## Develop an Image for Jupyterhub

[This Loom video](https://www.loom.com/share/1d3b00afe6314fccac55c0ce9b22ec02) walks through the process of creating and deploying new JupyterHub images that is found below.

In order to test new images for Jupyterhub

* create a new branch starting with development (e.g. `development`, `development-hub`).
* make changes to the Dockerfile as needed.
* a new image will automatically be built as a [calitp-py image](https://github.com/cal-itp/calitp-py/pkgs/container/calitp-py), named `calitp-py:<branch_name>`.

### Run an image on github container repository

You can test an image locally by running the following:

```
# note change the left-hand 8888 to another port, if you are already using that one
# if you are testing a different branch image, change development to that branch
docker run -p 8888:8888 -it --rm ghcr.io/cal-itp/calitp-py:development
```

Once this runs, you should be able to view it on `localhost:8888`.
Note that it should print a link in the terminal with a special token you may need to enter.

### Build and run an image using docker-compose

In order to build and test changes locally, you can run the following.

```
docker-compose build
docker-compose up
```

This will do two things to help with development:

* mount your local directory as `/home/jovyan/app`.
* mount your default gcloud credentials to the image.

If you do not have credentials set, you can use this command:

```
gcloud auth application-default login
```

## Release Image to Jupyterhub

This repo also handles pushing up a new jupyterhub image for calitp.
See the "Package docker image" section of [this workflow file](https://github.com/cal-itp/calitp-py/blob/main/.github/workflows/ci.yml).

The workflow publishes images to github container registry in two cases:

* a release with a tag that starts with `hub`
* a commit to any branch named development

The steps to update jupyterhub on the calitp cluster are as follows:

* create a calitp release, tagged as `hub-v<VERSION NUMBER>`, e.g. `hub-v1`
* check the corresponding action to ensure a new image was pushed. The image should appear on the [packages page](https://github.com/orgs/cal-itp/packages?repo_name=calitp-py).
* follow the instructions in the data-infra docs on [updating the jupyterhub deploy](https://docs.calitp.org/data-infra/kubernetes/JupyterHub.html#updating).
