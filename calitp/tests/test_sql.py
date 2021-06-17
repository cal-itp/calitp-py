import pandas as pd
import pytest

from calitp.sql import write_table
from contextlib import contextmanager
from calitp.config import RequiresAdminWarning
from calitp.tests.helpers import CI_TABLE_NAME


@contextmanager
def as_admin():
    import os

    prev_user = os.environ.get("CALITP_USER")

    os.environ["CALITP_USER"] = "admin"

    try:
        yield
    finally:
        if prev_user is None:
            del os.environ["CALITP_USER"]
        else:
            os.environ["CALITP_USER"] = prev_user


def test_write_table():
    df = pd.DataFrame({"x": [1, 2, 3]})

    with as_admin():
        write_table(df, f"{CI_TABLE_NAME}.testzzzz")


def test_write_table_noop():
    df = pd.DataFrame({"x": [1, 2, 3]})

    with pytest.warns(RequiresAdminWarning):
        write_table(df, f"{CI_TABLE_NAME}.testzzzz")
