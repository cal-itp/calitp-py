import pytest
import uuid

from calitp.config import get_bucket
from calitp.storage import get_fs


@pytest.fixture
def tmp_name():
    # generate a random table name. ensure it does not start with a number.
    yield str(uuid.uuid4())


def test_get_fs_pipe(tmp_name):
    bucket = get_bucket()
    bucket_dir = f"{bucket}/calitp/{tmp_name}"
    fname = f"{bucket_dir}/test.txt"

    fs = get_fs()
    fs.pipe(fname, "1".encode())

    res = fs.listdir(bucket_dir)
    assert len(res) == 1

    fs.cat(fname) == "1"
