import gcsfs

from .config import is_development, get_bucket, require_admin


def get_fs(gcs_project="cal-itp-data-infra"):
    if is_development():
        return gcsfs.GCSFileSystem(project=gcs_project, token="google_default")
    else:
        return gcsfs.GCSFileSystem(project=gcs_project, token="cloud")


@require_admin("save_to_gcfs")
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


def read_gcfs(
    src_path, dst_path=None, gcs_project="cal-itp-data-infra", bucket=None, verbose=True
):
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
