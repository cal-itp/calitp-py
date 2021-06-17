import os
from pathlib import Path


def is_development():
    options = {"development", "cal-itp-data-infra"}

    if os.environ["AIRFLOW_ENV"] not in options:
        raise ValueError("AIRFLOW_ENV variable must be one of %s" % options)

    return os.environ["AIRFLOW_ENV"] == "development"


def get_bucket():
    # TODO: can probably pull some of these behaviors into a config class
    if is_development():
        return "gs://gtfs-data-test"
    else:
        return "gs://gtfs-data"


def get_project_id():
    return "cal-itp-data-infra"


def format_table_name(name, is_staging=False, full_name=False):
    dataset, table_name = name.split(".")
    staging = "__staging" if is_staging else ""
    test_prefix = "zzz_test_" if is_development() else ""

    project_id = get_project_id() + "." if full_name else ""
    # e.g. test_gtfs_schedule__staging.agency

    return f"{project_id}{test_prefix}{dataset}.{table_name}{staging}"


def pipe_file_name(path):
    """Returns absolute path for a file in the pipeline (e.g. the data folder).

    """

    # For now, we just get the path relative to the directory holding the
    # DAGs folder. For some reason, gcp doesn't expose the same variable
    # for this folder, so need to handle differently on dev.
    if is_development():
        root = Path(os.environ["AIRFLOW__CORE__DAGS_FOLDER"]).parent
    else:
        root = Path(os.environ["DAGS_FOLDER"]).parent

    return str(root / path)
