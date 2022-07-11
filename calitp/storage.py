import abc
import base64
import gzip
import json
import logging
import os
import re
from enum import Enum
from typing import ClassVar, Dict, List, Optional, Type, Union, get_type_hints

import gcsfs
import humanize
import pendulum
from pydantic import BaseModel, Field, HttpUrl, validator
from pydantic.class_validators import root_validator
from pydantic.tools import parse_obj_as
from requests import Request
from typing_extensions import Annotated, Literal

from .config import get_bucket, is_cloud, is_development, require_pipeline


def get_fs(gcs_project="", **kwargs):
    if is_cloud():
        return gcsfs.GCSFileSystem(project=gcs_project, token="cloud", **kwargs)
    else:
        return gcsfs.GCSFileSystem(project=gcs_project, token="google_default", **kwargs)


@require_pipeline("save_to_gcfs")
def save_to_gcfs(
    src_path,
    dst_path,
    gcs_project="cal-itp-data-infra",
    bucket=None,
    use_pipe=False,
    verbose=True,
    **kwargs,
):
    """Convenience function for saving files from disk to google cloud storage.

    Arguments:
        src_path: path to file being saved.
        dst_path: path to bucket subdirectory (e.g. "path/to/dir").
    """

    bucket = get_bucket() if bucket is None else bucket

    full_dst_path = bucket + "/" + str(dst_path)

    fs = get_fs(gcs_project)

    if verbose:
        print("Saving to:", full_dst_path)

    if not use_pipe:
        fs.put(str(src_path), full_dst_path, **kwargs)
    else:
        fs.pipe(str(full_dst_path), src_path, **kwargs)

    return full_dst_path


def read_gcfs(src_path, dst_path=None, gcs_project="", bucket=None, verbose=True):
    """
    Arguments:
        src_path: path to file being read from google cloud.
        dst_path: optional path to save file directly on disk.
    """

    bucket = get_bucket() if bucket is None else bucket

    fs = get_fs(gcs_project)

    full_src_path = bucket + "/" + str(src_path)

    if verbose:
        print(f"Reading file: {full_src_path}")

    if dst_path is None:
        return fs.open(full_src_path)
    else:
        # TODO: in this case, dump directly to disk, rather opening
        raise NotImplementedError()

    return full_src_path


def make_name_bq_safe(name: str):
    """Replace non-word characters.
    See: https://cloud.google.com/bigquery/docs/reference/standard-sql/lexical#identifiers."""
    return str.lower(re.sub("[^\w]", "_", name))  # noqa: W605


def prefix_bucket(bucket):
    # TODO: use once we're in python 3.9+
    # bucket = bucket.removeprefix("gs://")
    bucket = bucket.replace("gs://", "")
    return f"gs://test-{bucket}" if is_development() else f"gs://{bucket}"


PARTITIONED_ARTIFACT_METADATA_KEY = "PARTITIONED_ARTIFACT_METADATA"

PartitionType = Union[str, int, pendulum.DateTime, pendulum.Date, pendulum.Time]

PARTITION_SERIALIZERS = {
    str: str,
    int: str,
    pendulum.DateTime: lambda dt: dt.to_iso8601_string(),
    pendulum.Date: lambda d: d.strftime("%Y-%m-%d"),
    pendulum.Time: lambda t: t.format("HH:mm:ss"),
}

PARTITION_DESERIALIZERS = {
    str: str,
    int: int,
    pendulum.DateTime: lambda s: pendulum.parse(s, exact=True),
    pendulum.Date: lambda s: pendulum.parse(s, exact=True),
    pendulum.Time: lambda s: pendulum.parse(s, exact=True),
}


def partition_map(path) -> Dict[str, PartitionType]:
    return {key: value for key, value in re.findall(r"/(\w+)=([\w\-:=]+)(?=/)", path.lower())}


# class GTFSFeedType(str, Enum):
#     schedule = "schedule"
#     rt = "rt"


class GTFSFeedType(str, Enum):
    schedule = "schedule"
    service_alerts = "service_alerts"
    trip_updates = "trip_updates"
    vehicle_positions = "vehicle_positions"


class AirtableGTFSDataRecord(BaseModel):
    name: str
    uri: Optional[str]
    data: GTFSFeedType
    data_quality_pipeline: Optional[bool]
    schedule_to_use_for_rt_validation: Optional[List[str]]
    auth_query_param: Dict[str, str] = {}
    # TODO: add auth_headers when available in Airtable!

    class Config:
        extra = "allow"

    @validator("data", pre=True, allow_reuse=True)
    def convert_feed_type(cls, v):
        if "schedule" in v.lower():
            return GTFSFeedType.schedule
        elif "vehicle" in v.lower():
            return GTFSFeedType.vehicle_positions
        elif "trip" in v.lower():
            return GTFSFeedType.trip_updates
        elif "alerts" in v.lower():
            return GTFSFeedType.service_alerts
        return v

    @property
    def schedule_url(self) -> Optional[HttpUrl]:
        # TODO: implement me
        raise NotImplementedError

    @property
    def auth_header(self) -> Dict[str, str]:
        return {}

    @property
    def base64_encoded_url(self) -> str:
        # see: https://docs.python.org/3/library/base64.html#base64.urlsafe_b64encode
        # we care about replacing slashes for GCS object names
        # can use: https://www.base64url.com/ to test encoding/decoding
        # convert in bigquery: https://cloud.google.com/bigquery/docs/reference/standard-sql/string_functions#from_base64
        return base64.urlsafe_b64encode(self.uri.encode()).decode()

    def build_request(self, auth_dict: dict) -> Request:
        params = {k: auth_dict[v] for k, v in self.auth_query_param.items()}
        headers = {k: auth_dict[v] for k, v in self.auth_header.items()}

        # some web servers require user agents or they will throw a 4XX error
        headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0"

        # inspired by: https://stackoverflow.com/questions/18869074/create-url-without-request-execution
        return Request(
            "GET",
            url=self.uri,
            params=params,
            headers=headers,
        )


class PartitionedGCSArtifact(BaseModel, abc.ABC):
    """
    This class is designed to be subclassed to model "extracts", i.e. a particular
    download of a given data source.
    """

    filename: str

    class Config:
        json_encoders = {
            pendulum.DateTime: lambda dt: dt.to_iso8601_string(),
        }

    @property
    @abc.abstractmethod
    def bucket(self) -> str:
        """Bucket name"""

    @property
    @abc.abstractmethod
    def table(self) -> str:
        """Table name"""

    @classmethod
    def bucket_table(cls) -> str:
        bucket = cls.bucket.replace("gs://", "")
        return f"gs://{bucket}/{cls.table}/"

    @property
    @abc.abstractmethod
    def partition_names(self) -> List[str]:
        """
        Defines the partitions into which this artifact is organized.
        The order does matter!
        """

    @property
    def partition_types(self) -> Dict[str, Type[PartitionType]]:
        return {}

    @root_validator(allow_reuse=True)
    def check_partitions(cls, values):
        cls_properties = [name for name in dir(cls) if isinstance(getattr(cls, name), property)]
        missing = [name for name in cls.partition_names if name not in values and name not in cls_properties]
        if missing:
            raise ValueError(f"all partition names must exist as fields or properties; missing {missing}")
        return values

    @property
    def path(self):
        return os.path.join(
            self.bucket,
            self.table,
            *[
                f"{name}={PARTITION_SERIALIZERS[type(getattr(self, name))](getattr(self, name))}"
                for name in self.partition_names
            ],
            self.filename,
        )

    def save_content(self, fs: gcsfs.GCSFileSystem, content: bytes, exclude=None):
        logging.info(f"saving {humanize.naturalsize(len(content))} to {self.path}")
        fs.pipe(path=self.path, value=content)
        fs.setxattrs(
            path=self.path,
            # This syntax seems silly but it's so we pass the _value_ of PARTITIONED_ARTIFACT_METADATA_KEY
            **{PARTITIONED_ARTIFACT_METADATA_KEY: self.json(exclude=exclude)},
        )


def fetch_all_in_partition(
    cls: Type[PartitionedGCSArtifact],
    fs: gcsfs.GCSFileSystem,
    bucket: str,
    table: str,
    partitions: Dict[str, PartitionType],
) -> List[Type[PartitionedGCSArtifact]]:
    path = "/".join(
        [
            bucket,
            table,
            *[f"{key}={value}" for key, value in partitions.items()],
        ]
    )
    files = parse_obj_as(
        GCSObjectInfoList,
        [v for _, _, files in list(fs.walk(path, detail=True)) for v in files.values()],
    )
    return [
        parse_obj_as(cls, json.loads(fs.getxattr(file.name, PARTITIONED_ARTIFACT_METADATA_KEY)))
        for file in files.__root__
    ]


class ProcessingOutcome(BaseModel, abc.ABC):
    success: bool
    exception: Optional[Exception]
    input_record: BaseModel

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {Exception: lambda e: str(e)}

    # TODO: is this really useful?
    @property
    @abc.abstractmethod
    def input_type(self) -> Type[PartitionedGCSArtifact]:
        """The input type that was processed to produce this outcome."""


class GCSBaseInfo(BaseModel, abc.ABC):
    bucket: str
    name: str

    class Config:
        extra = "ignore"

    @property
    @abc.abstractmethod
    def partition(self) -> Dict[str, str]:
        pass


class GCSFileInfo(GCSBaseInfo):
    type: Literal["file"]
    size: int
    md5Hash: str

    @property
    def filename(self) -> str:
        return os.path.basename(self.name)

    @property
    def partition(self) -> Dict[str, str]:
        return partition_map(self.name)


class GCSObjectInfoList(BaseModel):
    __root__: List["GCSObjectInfo"]


class GCSDirectoryInfo(GCSBaseInfo):
    type: Literal["directory"]

    @property
    def partition(self) -> Dict[str, str]:
        return partition_map(self.name + "/")

    def children(self, fs) -> List["GCSObjectInfo"]:
        # TODO: this should work with a discriminated type but idk why it's not
        return parse_obj_as(GCSObjectInfoList, [fs.info(child) for child in fs.ls(self.name)]).__root__


GCSObjectInfo = Annotated[
    Union[GCSFileInfo, GCSDirectoryInfo],
    Field(discriminator="type"),
]

GCSObjectInfoList.update_forward_refs()


# TODO: we could probably pass this a class
def get_latest_file(table_path: str, partitions: Dict[str, Type[PartitionType]]) -> GCSFileInfo:
    fs = get_fs()
    directory = GCSDirectoryInfo(**fs.info(table_path))

    for key, typ in partitions.items():
        directory = sorted(
            directory.children(fs),
            key=lambda o: PARTITION_DESERIALIZERS[typ](o.partition[key]),
            reverse=True,
        )[0]

    children = directory.children(fs)
    # This is just a convention for us for now; we could also label files with metadata if desired
    if len(children) != 1:
        raise ValueError(f"found {len(directory.children(fs))} files rather than 1 in the directory {directory.name}")

    ret = children[0]

    # is there a way to have pydantic check this?
    if not isinstance(ret, GCSFileInfo):
        raise ValueError(f"encountered unexpected type {type(ret)} rather than GCSFileInfo")

    return ret


class AirtableGTFSDataExtract(PartitionedGCSArtifact):
    bucket: ClassVar[str] = prefix_bucket("gs://calitp-airtable")
    table: ClassVar[str] = "california_transit__gtfs_datasets"
    partition_names: ClassVar[List[str]] = ["dt", "time"]
    dt: pendulum.Date
    time: pendulum.Time
    records: List[AirtableGTFSDataRecord]

    # TODO: this should probably be abstracted somewhere... it's useful in lots of places, probably
    @classmethod
    def get_latest(cls) -> "AirtableGTFSDataExtract":
        # TODO: this concatenation should live on the abstract base class probably
        latest = get_latest_file(
            cls.bucket_table(),
            partitions={name: get_type_hints(cls).get(name, str) for name in cls.partition_names},
        )

        logging.info(f"identified {latest.name} as the most recent extract of gtfs datasets")

        with get_fs().open(latest.name, "rb") as f:
            content = gzip.decompress(f.read()).decode()

        records = [AirtableGTFSDataRecord(**json.loads(row)) for row in content.splitlines()]

        return AirtableGTFSDataExtract(
            records=records,
            filename=latest.filename,
            dt=pendulum.parse(latest.partition["dt"], exact=True),
            time=pendulum.parse(latest.partition["time"], exact=True),
        )


class GTFSFeedExtractInfo(PartitionedGCSArtifact):
    # TODO: this should check whether the bucket exists https://stackoverflow.com/a/65628273
    # TODO: this should be named `gtfs-raw` _or_ we make it dynamic
    bucket: ClassVar[str] = prefix_bucket("gs://calitp-gtfs-schedule-raw")
    partition_names: ClassVar[List[str]] = ["dt", "base64_url", "time"]
    config: AirtableGTFSDataRecord
    response_code: int
    response_headers: Optional[Dict[str, str]]
    download_time: pendulum.DateTime

    @property
    def table(self) -> GTFSFeedType:
        return self.config.data

    @property
    def dt(self) -> pendulum.Date:
        return self.download_time.date()

    @property
    def base64_url(self) -> str:
        return self.config.base64_encoded_url

    @property
    def time(self) -> pendulum.Time:
        return self.download_time.time()


class AirtableGTFSDataRecordProcessingOutcome(ProcessingOutcome):
    input_type: ClassVar[Type[PartitionedGCSArtifact]] = GTFSFeedExtractInfo
    extract: Optional[GTFSFeedExtractInfo]


class DownloadFeedsResult(PartitionedGCSArtifact):
    bucket: ClassVar[str] = prefix_bucket("gs://calitp-gtfs-schedule-raw")
    table: ClassVar[str] = "download_schedule_feed_results"
    partition_names: ClassVar[List[str]] = ["dt", "time"]
    start_time: pendulum.DateTime
    end_time: pendulum.DateTime
    outcomes: List[AirtableGTFSDataRecordProcessingOutcome]

    @property
    def dt(self) -> pendulum.Date:
        return self.start_time.date()

    @property
    def time(self) -> pendulum.Time:
        return self.start_time.time()

    @property
    def successes(self) -> List[AirtableGTFSDataRecordProcessingOutcome]:
        return [outcome for outcome in self.outcomes if outcome.success]

    @property
    def failures(self) -> List[AirtableGTFSDataRecordProcessingOutcome]:
        return [outcome for outcome in self.outcomes if not outcome.success]

    # TODO: I dislike having to exclude the records here
    #   I need to figure out the best way to have a single type represent the "metadata" of
    #   the content as well as the content itself
    def save(self, fs):
        self.save_content(
            fs=fs,
            content="\n".join(o.json() for o in self.outcomes).encode(),
            exclude={"outcomes"},
        )
