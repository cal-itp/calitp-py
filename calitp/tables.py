from siuba.sql import LazyTbl

from .sql import get_engine
from .config import is_development


class AttributeDict:
    def __init__(self):
        self._d = {}

    def __getattr__(self, k):
        if k in self._d:
            return self._d[k]

        raise AttributeError("No attribute %s" % k)

    def __setitem__(self, k, v):
        self._d[k] = v

    def __dir__(self):
        return list(self._d.keys())


class AutoTable:
    def __init__(self, engine, table_formatter=None, table_filter=None):
        self._engine = engine
        self._table_formatter = table_formatter
        self._table_filter = table_filter
        self._table_names = tuple()
        self._accessors = {}

    def __getattr__(self, k):
        if k in self._accessors:
            return self._accessors[k]

        raise AttributeError("No such attribute %s" % k)

    def __dir__(self):
        return list(self._accessors.keys())

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
            schema, table = k.split(".")

            if schema not in self._accessors:
                self._accessors[schema] = AttributeDict()

            self._accessors[schema][table] = self._table_factory(v)

    def _table_factory(self, table_name):
        PrintTable(self, table_name)
        def loader():
            return self._load_table(table_name)

        return loader

    def _load_table(self, table_name):
       
        return LazyTbl(self._engine, table_name)

class PrintTable:
    def __init__(self,  table_name):
        self.table_name = table_name
        for i in tbl.tbl.columns.values():
            self.col_names = i.name
            print(self.col_names)

    def _repr_html_(self):
        return f"""
            <h3> {self.table_name} </h3>
            <table>
                <tr>
                    <th>name</th>
                    <th>description</th>
                </tr>
                <tr>
                     <td>{self.col_names}</td>
                    #not ideal
                    <td>{tbl.tbl.columns.values()[0:1]}</td>
                </tr>
            </table>
            """


tbl = AutoTable(
    get_engine(),
    lambda s: s,  # s.replace(".", "_"),
    lambda s: "zzz_test_" not in s if not is_development() else True,
)

tbl._init()
