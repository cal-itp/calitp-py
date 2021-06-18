import os
from calitp.sql import get_engine
from calitp.tests.helpers import CI_SCHEMA_NAME

os.environ["AIRFLOW_ENV"] = "development"

_engine = get_engine()
for _name in _engine.table_names(schema=f"zzz_test_{CI_SCHEMA_NAME}"):
    _engine.execute(f"DROP TABLE {_name};")
