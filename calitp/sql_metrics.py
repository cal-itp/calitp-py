from warnings import warn

# siuba imports that are stable
from siuba.dply.verbs import filter, select, inner_join, mutate, arrange
from siuba.dply.vector import lead
from siuba.sql import LazyTbl

# Note: these functions are being moved in siuba v1
from siuba.siu import _
from siuba.dply.verbs import singledispatch2, pipe

from collections.abc import MutableMapping
from functools import wraps

from .sql import get_engine


def warn_experimental(f):
    @wraps(f)
    def wrapper(*args, **kwargs):

        warn("SQL Metric configuration is experimental and may change")
        return f(*args, **kwargs)

    return wrapper


class Config(MutableMapping):
    def __init__(self, *args, **kwargs):
        self._d = dict(*args, **kwargs)

    def __getitem__(self, k):
        return self._d[k]

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    @warn_experimental
    def __delitem__(self, k):
        del self._d[k]

    @warn_experimental
    def __setitem__(self, k, v):
        self._d[k] = v


config = Config(dim_date_table="views.dim_date", far_future_date="2099-01-01")

f_pipe_identity = pipe(lambda d: d)


@singledispatch2(LazyTbl)
def cross_by_date(
    __data,
    expr_date_filter=None,
    col_created="calitp_extracted_at",
    col_deleted="calitp_deleted_at",
    date_table=None,
    far_future_date=None,
):

    """
    Argument:
        __data: a LazyTbl data source
        expr_date_filter: optional expression to filter date table on
        col_created: name of the created at column
        col_deleted: name of the deleted at column
        date_table (default: config.dim_date_table): table to use for date dimension
        far_future_date (default: config.far_future_date): date value for
            filling missing deleted at values

    Note:
        far_future_date is currently only used if col_deleted is None.

    """

    # configure date table ----

    if date_table is None:
        tbl_dates_raw = LazyTbl(get_engine(), config.get("dim_date_table"))
    elif isinstance(date_table, LazyTbl):
        tbl_dates_raw = date_table
    else:
        tbl_dates_raw = LazyTbl(get_engine(), date_table)

    if far_future_date is None:
        far_future_date = config.get("far_future_date")

    # filter date table using custom expression
    if expr_date_filter is not None:
        f_date_filter = filter(expr_date_filter)
    else:
        f_date_filter = f_pipe_identity

    tbl_dates = tbl_dates_raw >> f_date_filter >> select(_.full_date)

    # if we'll cross based on a single column, then use LEAD to create the deleted col
    if col_deleted is None:
        # TODO: this needs to set deleted at for the most recently created record
        col_deleted = "__calitp_deleted_at"
        f_mutate_deleted = arrange(_[col_created]) >> mutate(
            __calitp_deleted_at=lead(_[col_created]).fillna(far_future_date)
        )
    else:
        f_mutate_deleted = f_pipe_identity

    # perform join with date table and slowly changing dimension table ----
    return inner_join(
        __data >> f_mutate_deleted,
        tbl_dates >> f_date_filter,
        sql_on=lambda lhs, rhs: (lhs[col_created] <= rhs["full_date"])
        & (lhs[col_deleted] > rhs.full_date),
    )
