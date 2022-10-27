from typing import Mapping

import google_crc32c
from google.cloud import secretmanager

project = "projects/cal-itp-data-infra"


def get_secret_by_name(
    name: str,
    client=secretmanager.SecretManagerServiceClient(),
) -> str:

    version = f"{project}/secrets/{name}/versions/latest"
    response = client.access_secret_version(request={"name": version})

    crc32c = google_crc32c.Checksum()
    crc32c.update(response.payload.data)
    if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
        raise ValueError(f"Data corruption detected for secret {version}.")

    return response.payload.data.decode("UTF-8").strip()


def get_secrets_by_label(
    label: str,
    client=secretmanager.SecretManagerServiceClient(),
) -> Mapping[str, str]:

    filter_request = {
        "parent": project,
        "filter": f"labels.{label}:*",
    }

    secret_values = {}

    for secret in client.list_secrets(request=filter_request):
        version = f"{secret.name}/versions/latest"
        response = client.access_secret_version(request={"name": version})

        crc32c = google_crc32c.Checksum()
        crc32c.update(response.payload.data)
        if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
            raise ValueError(f"Data corruption detected for secret {version}.")

        secret_values[secret.name.split("/")[-1]] = response.payload.data.decode("UTF-8").strip()

    return secret_values


if __name__ == "__main__":
    print("loading secrets...")
    get_secret_by_name("BEAR_TRANSIT_KEY")
    print(get_secrets_by_label("gtfs_rt").keys())
