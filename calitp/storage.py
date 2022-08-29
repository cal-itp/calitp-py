import abc
import base64
import cgi
import gzip
import json
import logging
import os
import re
from abc import ABC
from datetime import datetime
from enum import Enum
from typing import ClassVar, Dict, List, Optional, Tuple, Type, Union, get_type_hints

import gcsfs
import humanize
import pendulum
from google.cloud import storage
from jinja2 import Environment, StrictUndefined, select_autoescape
from pydantic import BaseModel, Field, HttpUrl, constr, validator
from pydantic.class_validators import root_validator
from pydantic.tools import parse_obj_as
from requests import Request, Session
from typing_extensions import Annotated, Literal

from .config import get_bucket, is_cloud, require_pipeline

JSONL_EXTENSION = ".jsonl"
JSONL_GZIP_EXTENSION = f"{JSONL_EXTENSION}.gz"


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


AIRTABLE_BUCKET = os.getenv("CALITP_BUCKET__AIRTABLE")
SCHEDULE_RAW_BUCKET = os.getenv("CALITP_BUCKET__GTFS_SCHEDULE_RAW")
RT_RAW_BUCKET = os.getenv("CALITP_BUCKET__GTFS_RT_RAW")
DBT_ARTIFACT_BUCKET = os.getenv("CALITP_BUCKET__DBT_ARTIFACTS")
PUBLISH_BUCKET = os.getenv("CALITP_BUCKET__PUBLISH")

PARTITIONED_ARTIFACT_METADATA_KEY = "PARTITIONED_ARTIFACT_METADATA"

PartitionType = Union[str, int, pendulum.DateTime, pendulum.Date, pendulum.Time]

PARTITION_SERIALIZERS = {
    str: str,
    int: str,
    pendulum.Date: lambda d: d.to_date_string(),
    pendulum.DateTime: lambda dt: dt.to_iso8601_string(),
}

PARTITION_DESERIALIZERS = {
    str: str,
    int: int,
    pendulum.Date: lambda s: pendulum.parse(s, exact=True),
    pendulum.DateTime: lambda s: pendulum.parse(s, exact=True),
}


def partition_map(path) -> Dict[str, PartitionType]:
    return {key: value for key, value in re.findall(r"/(\w+)=([\w\-:=+.]+)(?=/)", path)}


def serialize_partitions(partitions: Dict[str, PartitionType]) -> List[str]:
    return [f"{name}={PARTITION_SERIALIZERS[type(value)](value)}" for name, value in partitions.items()]


class GTFSFeedType(str, Enum):
    schedule = "schedule"
    service_alerts = "service_alerts"
    trip_updates = "trip_updates"
    vehicle_positions = "vehicle_positions"

    @property
    def is_rt(self) -> bool:
        if self == GTFSFeedType.schedule:
            return False
        if self in (
            GTFSFeedType.service_alerts,
            GTFSFeedType.trip_updates,
            GTFSFeedType.vehicle_positions,
        ):
            return True
        raise RuntimeError(f"managed to end up with an invalid enum type of {self}")


class AirtableGTFSDataRecord(BaseModel):
    id: str
    name: str
    uri: Optional[str]
    data: Optional[GTFSFeedType]
    data_quality_pipeline: Optional[bool]
    schedule_to_use_for_rt_validation: Optional[List[str]]
    auth_query_param: Dict[str, str] = {}

    class Config:
        extra = "allow"

    # TODO: this is a bit hacky but we need this until we split off auth query params from the URI itself
    @root_validator(pre=True, allow_reuse=True)
    def parse_query_params(cls, values):
        if values.get("uri"):
            jinja_pattern = r"(?P<param_name>\w+)={{\s*(?P<param_lookup_key>\w+)\s*}}&?"
            match = re.search(jinja_pattern, values["uri"])
            if match:
                values["auth_query_param"] = {match.group("param_name"): match.group("param_lookup_key")}
                values["uri"] = re.sub(jinja_pattern, "", values["uri"])
            elif "api.511.org" in values["uri"]:
                values["auth_query_param"] = {"api_key": "MTC_511_API_KEY"}
        return values

    @validator("uri", pre=True, allow_reuse=True)
    def handle_remaining_jinja(cls, v):
        if v:
            data = {
                "GRAAS_SERVER_URL": os.environ["GRAAS_SERVER_URL"],
            }
            return Environment(autoescape=select_autoescape(), undefined=StrictUndefined).from_string(v).render(**data)
        return v

    @validator("data", pre=True, allow_reuse=True)
    def convert_feed_type(cls, v):
        if not v:
            return None

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

    # TODO: this should actually rely on airtable data!
    @property
    def auth_header(self) -> Dict[str, str]:
        if self.uri:
            if "goswift.ly" in self.uri:
                return {
                    "authorization": "SWIFTLY_AUTHORIZATION_KEY_CALITP",
                }
            if "west-hollywood" in self.uri:
                return {
                    "x-umo-iq-api-key": "WEHO_RT_KEY",
                }
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

    filename: constr(strip_whitespace=True)

    class Config:
        json_encoders = {
            pendulum.DateTime: lambda dt: dt.to_iso8601_string(),
        }

    @property
    @abc.abstractmethod
    def bucket(self) -> str:
        """Bucket name"""

    @validator("bucket", check_fields=False, allow_reuse=True)
    def bucket_exists(cls, v):
        if not storage.Client().bucket(v).exists():
            raise ValueError(f"bucket {v} does not exist")

    @property
    @abc.abstractmethod
    def table(self) -> str:
        """Table name"""

    @property
    @abc.abstractmethod
    def partition_names(self) -> List[str]:
        """
        Defines the partitions into which this artifact is organized.
        The order does matter!
        """

    @property
    def serialized_partitions(self) -> List[str]:
        return serialize_partitions({name: getattr(self, name) for name in self.partition_names})

    @property
    def partition_types(self) -> Dict[str, Type[PartitionType]]:
        return {}

    @root_validator(allow_reuse=True)
    def check_partitions(cls, values):
        # TODO: this isn't great but some partition_names are properties
        if isinstance(cls.partition_names, property):
            return values
        cls_properties = [name for name in dir(cls) if isinstance(getattr(cls, name), property)]
        missing = [name for name in cls.partition_names if name not in values and name not in cls_properties]
        if missing:
            raise ValueError(f"all partition names must exist as fields or properties; missing {missing}")
        return values

    @property
    def name(self):
        return os.path.join(
            self.table,
            *self.serialized_partitions,
            self.filename,
        )

    # This exists because with gcsfs we pretend everything is a path rather than an object in a bucket
    @property
    def path(self):
        return os.path.join(self.bucket, self.name)

    def save_content(self, content: bytes, exclude=None, fs: gcsfs.GCSFileSystem = None, client: storage.Client = None):
        if (fs is None) == (client is None):
            raise TypeError("must provide a gcsfs file system OR a storage client")

        if fs:
            logging.info(f"saving {humanize.naturalsize(len(content))} to {self.path}")
            fs.pipe(path=self.path, value=content)
            fs.setxattrs(
                path=self.path,
                # This syntax seems silly but it's so we pass the _value_ of PARTITIONED_ARTIFACT_METADATA_KEY
                **{PARTITIONED_ARTIFACT_METADATA_KEY: self.json(exclude=exclude)},
            )

        if client:
            logging.info(f"saving {humanize.naturalsize(len(content))} to {self.bucket} {self.name}")
            blob = storage.Blob(
                name=self.name,
                bucket=client.bucket(self.bucket.replace("gs://", "")),
            )

            blob.upload_from_string(
                data=content,
                content_type="application/octet-stream",
                client=client,
            )

            blob.metadata = {PARTITIONED_ARTIFACT_METADATA_KEY: self.json(exclude=exclude)}
            blob.patch()


def fetch_all_in_partition(
    cls: Type[PartitionedGCSArtifact],
    fs: gcsfs.GCSFileSystem,
    partitions: Dict[str, PartitionType],
    bucket: str = None,
    table: str = None,
    verbose=False,
    progress=False,
) -> List[Type[PartitionedGCSArtifact]]:
    if not bucket:
        bucket = cls.bucket

        if not isinstance(bucket, str):
            raise TypeError(f"must either pass bucket, or the bucket must resolve to a string; got {type(bucket)}")

    if not table:
        table = cls.table

        if not isinstance(table, str):
            raise TypeError(f"must either pass table, or the table must resolve to a string; got {type(table)}")

    prefix = "/".join(
        [
            table,
            *serialize_partitions(partitions),
            "",
        ]
    )
    if verbose:
        print(f"listing all files in {bucket}/{prefix}")
    client = storage.Client()
    # once Airflow is upgraded to Python 3.9, can use:
    # files = client.list_blobs(bucket.removeprefix("gs://"), prefix=prefix, delimiter=None)
    files = client.list_blobs(re.sub(r"^gs://", "", bucket), prefix=prefix, delimiter=None)
    parsed = [parse_obj_as(cls, json.loads(file.metadata[PARTITIONED_ARTIFACT_METADATA_KEY])) for file in files]

    # This is a safeguard in case files were moved without their metadata being updated...
    for name, value in partitions.items():
        unexpected = {getattr(o, name) for o in parsed} - {value}
        assert not unexpected, f"found unexpected values for {name}: {unexpected}"

    return parsed


class ProcessingOutcome(BaseModel, abc.ABC):
    success: bool
    exception: Optional[Exception]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {Exception: lambda e: str(e)}


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
def get_latest_file(
    bucket: str,
    table: str,
    prefix_partitions: Dict[str, PartitionType],
    partition_types: Dict[str, Type[PartitionType]],
) -> GCSFileInfo:
    fs = get_fs()
    fs.invalidate_cache()

    prefix_info = fs.info("/".join([bucket, table, *serialize_partitions(prefix_partitions), ""]))
    directory = GCSDirectoryInfo(**prefix_info)

    for key, typ in partition_types.items():
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
    bucket: ClassVar[str] = AIRTABLE_BUCKET
    table: ClassVar[str] = "california_transit__gtfs_datasets"
    partition_names: ClassVar[List[str]] = ["dt", "ts"]
    ts: pendulum.DateTime
    records: List[AirtableGTFSDataRecord]

    @property
    def dt(self) -> pendulum.Date:
        return self.ts.date()

    # TODO: this should probably be abstracted somewhere... it's useful in lots of places, probably
    @classmethod
    def get_latest(cls) -> "AirtableGTFSDataExtract":
        latest = get_latest_file(
            cls.bucket,
            cls.table,
            prefix_partitions={},
            # TODO: this doesn't pick up the type hint of dt since it's a property; it's fine as a string but we should fix
            partition_types={name: get_type_hints(cls).get(name, str) for name in cls.partition_names},
        )

        logging.info(f"identified {latest.name} as the most recent extract of gtfs datasets")

        with get_fs().open(latest.name, "rb") as f:
            content = gzip.decompress(f.read())

        return AirtableGTFSDataExtract(
            filename=latest.filename,
            ts=pendulum.parse(latest.partition["ts"], exact=True),
            records=[AirtableGTFSDataRecord(**json.loads(row)) for row in content.decode().splitlines()],
        )


class GTFSFeedExtract(PartitionedGCSArtifact, ABC):
    ts: pendulum.DateTime
    config: AirtableGTFSDataRecord
    response_code: int
    response_headers: Optional[Dict[str, str]]

    @validator("ts", allow_reuse=True)
    def coerce_ts(cls, v):
        if isinstance(v, datetime):
            return pendulum.instance(v)
        return v

    @property
    def feed_type(self) -> GTFSFeedType:
        return self.config.data

    @property
    def dt(self) -> pendulum.Date:
        return self.ts.date()

    @property
    def hour(self) -> pendulum.DateTime:
        return self.ts.replace(minute=0, second=0, microsecond=0)

    @property
    def base64_url(self) -> str:
        return self.config.base64_encoded_url


class GTFSScheduleFeedExtract(GTFSFeedExtract):
    bucket: ClassVar[str] = SCHEDULE_RAW_BUCKET
    table: ClassVar[str] = GTFSFeedType.schedule
    feed_type: ClassVar[str] = GTFSFeedType.schedule
    partition_names: ClassVar[List[str]] = ["dt", "base64_url", "ts"]

    @validator("config", allow_reuse=True)
    def is_schedule_type(cls, v: AirtableGTFSDataRecord):
        if v.data != GTFSFeedType.schedule:
            raise TypeError("a schedule extract must come from a schedule config")
        return v


class GTFSRTFeedExtract(GTFSFeedExtract):
    bucket: ClassVar[str] = RT_RAW_BUCKET
    partition_names: ClassVar[List[str]] = ["dt", "hour", "ts", "base64_url"]

    @validator("config", allow_reuse=True)
    def is_rt_type(cls, v: AirtableGTFSDataRecord):
        if not v.data.is_rt:
            raise TypeError("a realtime extract must come from a realtime config")
        return v

    @property
    def table(self) -> str:
        return self.config.data

    @property
    def timestamped_filename(self):
        """
        Used for RT validation; it's faster to download and validate many files at once, and we need to identify
        them on disk.
        """
        return str(self.filename) + self.ts.strftime("__%Y-%m-%dT%H:%M:%SZ")


def download_feed(
    record: AirtableGTFSDataRecord,
    auth_dict: Dict,
    ts: pendulum.DateTime,
    default_filename="feed",
) -> Tuple[GTFSFeedExtract, bytes]:
    parse_obj_as(HttpUrl, record.uri)

    s = Session()
    r = s.prepare_request(record.build_request(auth_dict))
    resp = s.send(r)
    resp.raise_for_status()

    disposition_header = resp.headers.get("content-disposition", resp.headers.get("Content-Disposition"))

    if disposition_header:
        if disposition_header.startswith("filename="):
            # sorry; cgi won't parse unless it's prefixed with the disposition type
            disposition_header = f"attachment; {disposition_header}"
        _, params = cgi.parse_header(disposition_header)
        disposition_filename = params.get("filename")
    else:
        disposition_filename = None

    filename = (
        disposition_filename or (os.path.basename(resp.url) if resp.url.endswith(".zip") else None) or default_filename
    )

    extract_class = GTFSRTFeedExtract if record.data.is_rt else GTFSScheduleFeedExtract
    extract = extract_class(
        filename=filename,
        config=record,
        response_code=resp.status_code,
        response_headers=resp.headers,
        ts=ts,
    )

    return extract, resp.content


class DbtArtifact(PartitionedGCSArtifact):
    bucket: ClassVar[str] = DBT_ARTIFACT_BUCKET
    table: str
    ts: pendulum.DateTime
    partition_names: ClassVar[List[str]] = ["dt", "ts"]

    def dt(self) -> pendulum.Date:
        return self.ts.date()


class PublishArtifact(PartitionedGCSArtifact):
    bucket: ClassVar[str] = PUBLISH_BUCKET
    table: str
    ts: pendulum.DateTime
    partition_names: ClassVar[List[str]] = ["dt", "ts"]

    def dt(self) -> pendulum.Date:
        return self.ts.date()


if __name__ == "__main__":
    # just some useful testing stuff
    print(AirtableGTFSDataExtract.get_latest().path)

    # use Etc/UTC instead of UTC
    # Etc/UTC is what the pods get as a timezone... and it serializes to 2022-08-18T00:00:00+00:00
    # whereas UTC serializes to 2022-08-18T00:00:00Z
    # this should probably be checked in the partitioned artifact?
    yesterday_noon = pendulum.yesterday("Etc/UTC").replace(minute=0, second=0, microsecond=0)
    vp_files = fetch_all_in_partition(
        cls=GTFSRTFeedExtract,
        fs=get_fs(),
        partitions={
            "dt": yesterday_noon.date(),
            "hour": yesterday_noon,
        },
        table=GTFSFeedType.vehicle_positions,
        verbose=True,
        progress=True,
    )
    print(len(vp_files))

    schedule_files = fetch_all_in_partition(
        cls=GTFSScheduleFeedExtract,
        fs=get_fs(),
        partitions={
            "dt": pendulum.parse("2022-08-17", exact=True),
        },
        verbose=True,
        progress=True,
    )
    print(len(schedule_files))
    latest_schedule = get_latest_file(
        bucket=SCHEDULE_RAW_BUCKET,
        table=GTFSFeedType.schedule,
        prefix_partitions={
            "dt": pendulum.parse("2022-08-12", exact=True),
            "base64_url": "aHR0cHM6Ly9yaWRlbXZnby5vcmcvZ3Rmcw==",
        },
        partition_types={
            "ts": pendulum.DateTime,
        },
    )
    print(latest_schedule)
