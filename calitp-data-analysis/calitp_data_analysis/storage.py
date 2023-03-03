import os
from enum import Enum
from functools import partial
from typing import Any, Dict, List, Union

import geopandas as gpd
import pandas as pd
import pandas._testing as pd_testing
import pendulum
from tqdm.autonotebook import tqdm

# gs://calitp-publish-data-analysis
CALITP_BUCKET__PUBLISH_DATA_ANALYSIS = os.getenv("CALITP_BUCKET__PUBLISH_DATA_ANALYSIS")


class FileType(Enum):
    csv = "csv"
    jsonl = "jsonl"
    geojson = "geojson"


# copied from calitp-data-infra
PARTITION_SERIALIZERS = {
    str: str,
    int: str,
    pendulum.Date: lambda d: d.to_date_string(),
    pendulum.DateTime: lambda dt: dt.to_iso8601_string(),
}


def convert_pandas_type(item: Any) -> Union[str, int, pendulum.Date, pendulum.DateTime]:
    if isinstance(item, (str, int)):
        return item
    if isinstance(item, pd.Timestamp):
        return pendulum.instance(item)
    raise RuntimeError(f"invalid type {type(item)} for serialization")


def save_partitioned_dataframe(
    df: Union[pd.DataFrame, gpd.GeoDataFrame],
    table: str,
    partition_by: Union[str, List[str]],
    filetype="csv",
    bucket: str = None,
    filename: str = "data",
    verbose: bool = False,
    progress: bool = True,
    **write_kwargs,
) -> Dict[str, str]:
    if not bucket:
        bucket = CALITP_BUCKET__PUBLISH_DATA_ANALYSIS

    if not bucket:
        raise KeyError("must provide bucket or set CALITP_BUCKET__PUBLISH_DATA_ANALYSIS environment variable")

    if not bucket.startswith("gs://"):
        bucket = f"gs://{bucket}"

    bucket_table = f"{bucket.rstrip('/')}/{table}"
    paths = {}
    grouped = df.groupby(partition_by)
    print_f = print

    if progress:
        grouped = tqdm(grouped, desc=bucket_table)
        print_f = grouped.write

    for name, group in grouped:
        if filetype == "csv":
            write_func = partial(group.to_csv, **write_kwargs)
            extension = ".csv"
        elif filetype == "json":
            write_func = partial(group.to_json, orient="records", lines=True, **write_kwargs)
            extension = ".jsonl"
        else:
            raise ValueError(f"unknown filetype {filetype}")
        # I'm manually implementing this here but we probably should be handling this via PartitionedGCSArtifact
        if isinstance(partition_by, str):
            partition_path = f"{partition_by[0]}={PARTITION_SERIALIZERS[type(name)](name)}"
        else:
            partition_path = "/".join(
                f"{key}={PARTITION_SERIALIZERS[type(value)](value)}"
                for key, value in zip(partition_by, [convert_pandas_type(elem) for elem in name])
            )
        path = f"{bucket_table}/{partition_path}/{filename}{extension}"
        if verbose:
            print_f(f"Saving partition {name} to {path}")
        write_func(path_or_buf=path)
        paths[str(name)] = path
    return paths


if __name__ == "__main__":
    pd_testing.makeMixedDataFrame().to_parquet(
        f"{CALITP_BUCKET__PUBLISH_DATA_ANALYSIS}/mixed_data_frame_parquet/output.parquet", partition_cols=["C"]
    )
    save_partitioned_dataframe(
        df=pd_testing.makeMixedDataFrame(),
        table="mixed_data_frame",
        partition_by="C",
        verbose=True,
    )
    save_partitioned_dataframe(
        df=pd_testing.makeMixedDataFrame(),
        table="mixed_data_frame_multiple",
        partition_by=["C", "D"],
        verbose=True,
    )
