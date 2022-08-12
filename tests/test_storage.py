import uuid

import pytest
from pydantic import ValidationError

from calitp.config import get_bucket
from calitp.storage import AirtableGTFSDataRecord, get_fs

GCS_BUCKET = "gs://calitp-py-ci"


@pytest.fixture
def tmp_name():
    # generate a random table name. ensure it does not start with a number.
    name = f"{GCS_BUCKET}/calitp-" + str(uuid.uuid4())
    yield name

    try:
        fs = get_fs()
        fs.rm(tmp_name, recursive=True)
    except Exception:
        UserWarning("GCS folder not deleted: %s" % name)


def test_get_fs_pipe(tmp_name):
    bucket = get_bucket()
    bucket_dir = f"{bucket}/calitp/{tmp_name}"
    fname = f"{bucket_dir}/test.txt"

    fs = get_fs()
    fs.pipe(fname, "1".encode())

    res = fs.listdir(bucket_dir)
    assert len(res) == 1


def test_airtable_gtfs_data_record_handles_weird_inputs() -> None:
    AirtableGTFSDataRecord(
        name="some valid name",
        data=None,
    )
    AirtableGTFSDataRecord(
        name="some valid name",
        data="",
    )

    with pytest.raises(ValidationError):
        AirtableGTFSDataRecord(
            name="some valid name",
            data="invalid string",
        )
