import datetime
import json
import random

from google.protobuf import json_format
from google.transit import gtfs_realtime_pb2

from calitp.storage import get_fs


def get_random_protobuff(glob, bucket="gtfs-data", date="", format="protobuff"):
    date = date.strip("*")  # ignore ending asterix
    if len(date) < len("2022-01-01"):
        raise ValueError("You must at least specify YYYY-MM-DD in the date string.")
    if len(date) > len("2022-01-01T00:00:"):
        # user is specifying full time stamp
        date = date + "*"
    else:
        # This ensures that a date like 2022-01-01 is like 2022-01-01T00:00*
        # This way we are prefixing on everything up to the seconds
        today = datetime.date.today().replace(day=1)
        today = datetime.datetime.fromisoformat(today.isoformat()).isoformat()
        default_date = str(today).rsplit(":", 1)[0] + "*"
        date = date + default_date[len(date) :]

    # defines the proto schema I think
    feed = gtfs_realtime_pb2.FeedMessage()
    fs = get_fs()
    glob = glob + "*"
    glob = f"gs://{bucket}/rt/{date}/{glob}"
    blobs = fs.glob(glob)
    if len(blobs) == 0:
        raise Exception(f"No files were found matching glob {glob}")
    blob = random.choice(blobs)

    with fs.open(blob, "rb") as f:
        result = f.read()
        feed.ParseFromString(result)

    if not str(feed):
        error = "ERROR: File could not be parsed as a protobuff."
        error += " Displaying raw file instead."
        return blob, result.decode(encoding="utf-8"), error
    if format == "json":
        feed = json.dumps(json_format.MessageToDict(feed), indent=2)
    return blob, feed, None
