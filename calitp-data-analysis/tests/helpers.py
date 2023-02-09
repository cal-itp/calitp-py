from contextlib import contextmanager

CI_SCHEMA_NAME = "calitp_py"


@contextmanager
def as_calitp_user(user):
    import os

    prev_user = os.environ.get("CALITP_USER")

    os.environ["CALITP_USER"] = user

    try:
        yield
    finally:
        if prev_user is None:
            del os.environ["CALITP_USER"]
        else:
            os.environ["CALITP_USER"] = prev_user
