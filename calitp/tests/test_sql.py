import pandas as pd
import pytest
import uuid

from calitp.sql import get_table, write_table, query_sql, get_engine, sql_patch_comments
from calitp.config import RequiresAdminWarning, pipeline_context
from calitp.tests.helpers import CI_SCHEMA_NAME

from pandas.testing import assert_frame_equal

# TODO: set up a separate project for CI, so our CI doesn't have permission
# to create / delete prod tables. Bigquery lets you set read access on individual
# datasets, but write access happens at the project level. Working around now
# by creating a table outside CI, then only testing reading it.


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

    with pipeline_context():
        write_table(df, tmp_name)


def test_write_table_no_admin(tmp_name):
    df = pd.DataFrame({"x": [1, 2, 3]})

    with pytest.warns(RequiresAdminWarning):
        write_table(df, tmp_name)


def test_get_table(tmp_name):
    df = pd.DataFrame({"x": [1, 2, 3]})
    with pipeline_context():
        write_table(df, tmp_name)

    tbl_test = get_table(tmp_name, as_df=True)
    assert_frame_equal(tbl_test, df)


def test_query_sql():
    import tempfile
    import datetime

    from pathlib import Path
    from calitp.templates import user_defined_macros

    with tempfile.TemporaryDirectory() as dir_name:
        p_query = Path(dir_name) / "query.yml"
        p_query.write_text("""sql: SELECT {{THE_FUTURE}}""")

        query_txt = query_sql(str(p_query), dry_run=True, as_df=False)
        assert query_txt == f"SELECT {user_defined_macros['THE_FUTURE']}"

        res = query_sql(str(p_query), as_df=False)
        assert res.fetchall() == [(datetime.date(2099, 1, 1),)]


def test_query_sql_as_df():
    df = query_sql("SELECT 1 AS n")
    assert len(df) == 1
    assert "n" in df.columns


def test_patch_table_comments(tmp_name):
    from sqlalchemy import Table, MetaData

    engine = get_engine()

    df = pd.DataFrame({"x": [1, 2, 3]})
    with pipeline_context():
        write_table(df, tmp_name)

    sql_patch_comments(tmp_name, {"x": "x column"}, "some table")

    tbl_test = Table(tmp_name, MetaData(), autoload_with=engine)
    tbl_test.comment == "some table"
    tbl_test.c.x.comment == "x column"
