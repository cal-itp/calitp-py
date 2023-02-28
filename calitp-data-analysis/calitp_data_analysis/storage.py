import os
from enum import Enum
from functools import partial
from typing import List

import pandas as pd
import geopandas as gpd
from pandas import util

# gs://calitp-publish-data-analysis
CALITP_BUCKET__PUBLISH_DATA_ANALYSIS = os.getenv("CALITP_BUCKET__PUBLISH_DATA_ANALYSIS")

class FileType(Enum):
    csv = 'csv'
    jsonl = 'jsonl'
    geojson = 'geojson'

def save_partitioned_dataframe(df: Union[pd.DataFrame, gpd.DataFrame], table: str, partition_columns: List[str], filetype='csv', bucket: str = None, **write_kwargs) -> List[str]
    if not bucket:
        bucket = CALITP_BUCKET__PUBLISH_DATA_ANALYSIS

    if not bucket:
        raise KeyError("must provide bucket or set CALITP_BUCKET__PUBLISH_DATA_ANALYSIS environment variable")

    if not bucket.startswith("gs://"):
        bucket = f"gs://{bucket}"
    df.to_file(geojsonl_fpath, driver="GeoJSONSeq")
    grouped = df.groupby(partition_columns)

    for name, group in grouped:
        if filetype == 'csv':
            write_func = partial(group.to_csv, **write_kwargs)
            extension = '.csv'
        elif filetype == 'json':
            write_func = partial(group.to_json, orient='records', lines=True, **write_kwargs)
            extension = '.jsonl'
        else:
            raise ValueError(f"unknown filetype {filetype}")
        # I'm manually implementing this here but we probably should be handling this via PartitionedGCSArtifact
        write_func(path=f"{CALITP_BUCKET__PUBLISH_DATA_ANALYSIS}/{table}/{extension}")

if __name__ == '__main__':
    save_partitioned_dataframe(df=util.testing.makeMixedDataFrame(),
                               table="mixed_data_frame",

                               )
