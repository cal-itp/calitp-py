from siuba.sql import LazyTbl

from .sql import get_engine
from .config import is_development


class AutoTable:
    def __init__(self, engine, table_formatter=None, table_filter=None):
        self._engine = engine
        self._table_formatter = table_formatter
        self._table_filter = table_filter
        self._table_names = tuple()

    def _init(self):
        # remove any previously initialized attributes ----
        prev_table_names = self._table_names
        for k in prev_table_names:
            del self.__dict__[k]

        # initialize ----
        self._table_names = tuple(self._engine.table_names())

        mappings = {}
        for name in self._table_names:
            if self._table_filter is not None and not self._table_filter(name):
                continue

            fmt_name = self._table_formatter(name)
            if fmt_name in mappings:
                raise Exception("multiple tables w/ formatted name: %s" % fmt_name)
            mappings[fmt_name] = name

        self._attach_mappings(mappings)

    def _attach_mappings(self, mappings):
        for k, v in mappings.items():
            setattr(self, k, self._table_factory(v))

    def _table_factory(self, table_name):
        def loader():
            return self._load_table(table_name)

        return loader

    def _load_table(self, table_name):
        return LazyTbl(self._engine, table_name)


tbl = AutoTable(
    get_engine(),
    lambda s: s.replace(".", "_"),
    lambda s: "zzz_test_" not in s if not is_development() else True,
)

tbl._init()
