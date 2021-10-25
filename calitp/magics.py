from IPython.core.magic import (register_cell_magic)
from calitp.sql import query_sql

@register_cell_magic
def sql(line, cell):
    return query_sql(cell)
