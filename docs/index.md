# calitp

```python
from calitp.tables import tbl
from calitp.import query_sql


```

### metabase


![](assets/issue_329.png)


### siuba

```python
tbl.gtfs_schedule.agency()
```

### sql

```python
query_sql("""

SELECT COUNT(*) AS n
FROM gtfs_schedule.agency

""")
```
