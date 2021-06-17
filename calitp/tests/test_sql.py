import pandas as pd
import pytest

from calitp.sql import to_snakecase, write_table

CI_TABLE_NAME="calitp_py"


def test_write_table():
    df = pd.DataFrame({'x': [1,2,3]})

    write_table(df, f"{CI_TABLE_NAME}.testzzzz")
