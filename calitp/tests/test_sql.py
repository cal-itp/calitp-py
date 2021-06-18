import pandas as pd
import pytest
import uuid

from calitp.sql import get_table, write_table
from contextlib import contextmanager
from calitp.config import RequiresAdminWarning
from calitp.tests.helpers import CI_SCHEMA_NAME

from pandas.testing import assert_frame_equal

# TODO: set up a separate project for CI, so our CI doesn't have permission
# to create / delete prod tables. Bigquery lets you set read access on individual
# datasets, but write access happens at the project level. Working around now
# by creating a table outside CI, then only testing reading it.


@contextmanager
def as_pipeline():
    import os

    prev_user = os.environ.get("CALITP_USER")

    os.environ["CALITP_USER"] = "pipeline"

    try:
        yield
    finally:
        if prev_user is None:
            del os.environ["CALITP_USER"]
        else:
            os.environ["CALITP_USER"] = prev_user


@pytest.fixture
def tmp_name():
    from sqlalchemy.exc import NoSuchTableError

    # generate a random table name. ensure it does not start with a number.
    table_name = "t_" + str(uuid.uuid4()).replace("-", "_")
    schema_table = f"{CI_SCHEMA_NAME}.{table_name}"

    yield schema_table

    try:
        tbl = get_table(schema_table)
        tbl.drop()
    except NoSuchTableError:
        pass


@pytest.mark.skip
def test_write_table(tmp_name):
    df = pd.DataFrame({"x": [1, 2, 3]})

    with as_pipeline():
        write_table(df, tmp_name)


def test_write_table_no_admin(tmp_name):
    df = pd.DataFrame({"x": [1, 2, 3]})

    with pytest.warns(RequiresAdminWarning):
        write_table(df, tmp_name)


def test_get_table(tmp_name):
    df = pd.DataFrame({"x": [1, 2, 3]})
    with as_pipeline():
        write_table(df, tmp_name)

    tbl_test = get_table(tmp_name, as_df=True)
    assert_frame_equal(tbl_test, df)
