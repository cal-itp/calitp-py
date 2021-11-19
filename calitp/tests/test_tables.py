import pytest
import uuid
import pandas as pd

from calitp.sql import get_table, write_table, get_engine
from calitp.tables import AutoTable
from siuba.sql import LazyTbl

from contextlib import contextmanager
from calitp.tests.helpers import CI_SCHEMA_NAME


# TODO: copied from tests.sql, consolidate into helpers
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

    # Code that runs before test ----

    # generate a random table name. ensure it does not start with a number.
    table_name = "t_" + str(uuid.uuid4()).replace("-", "_")
    schema_table = f"{CI_SCHEMA_NAME}.{table_name}"

    # pass the name of the temporary table into the test
    yield schema_table

    # Code that runs after test ----
    # delete table corresponding to temporary name, if it exists
    try:
        tbl = get_table(schema_table)
        tbl.drop()
    except NoSuchTableError:
        pass


def test_write_table(tmp_name):
    schema_name, table_name = tmp_name.split(".")

    df = pd.DataFrame({"x": [1, 2, 3]})

    with as_pipeline():
        write_table(df, tmp_name)

    tbl = AutoTable(get_engine(), lambda s: s, lambda s: True,)  # s.replace(".", "_"),

    tbl._init()

    tbl_tmp = getattr(tbl.calitp_py, table_name)()

    assert isinstance(tbl_tmp, LazyTbl)


def test_auto_table_comments(tmp_name):
    from calitp.tables import TableFactory

    get_engine().execute(
        f"""
        CREATE TABLE `{tmp_name}` (
            x INT64 OPTIONS(description="x column"),
            y STRING OPTIONS(description="y column")
        )
        OPTIONS(
            description="the table comment"
        )
    """
    )

    # TODO: rather than using AutoTable, let's just use CalitpTable directly
    tbl_factory_tmp = TableFactory(get_engine(), tmp_name)
    doc = tbl_factory_tmp._repr_html_()

    assert "x column" in doc
    assert "the table comment" in doc
