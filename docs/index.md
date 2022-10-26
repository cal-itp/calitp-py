# calitp

```python
from calitp.tables import tbls
from calitp. import query_sql


```

### metabase


![](assets/issue_329.png)


### siuba

```python
tbls.gtfs_schedule.agency()
```

### sql

```python
query_sql("""

SELECT COUNT(*) AS n
FROM gtfs_schedule.agency

""")
```
