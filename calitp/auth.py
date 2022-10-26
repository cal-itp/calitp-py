import os
from typing import Mapping, Sequence

import google_crc32c
from google.cloud import secretmanager

AUTH_KEYS_ENV_VAR = "CALITP_AUTH_KEYS"
DEFAULT_AUTH_KEYS = tuple(os.environ[AUTH_KEYS_ENV_VAR].split(",")) if AUTH_KEYS_ENV_VAR in os.environ else tuple()


def get_secrets(
    keys: Sequence[str] = DEFAULT_AUTH_KEYS,
    secret_client=secretmanager.SecretManagerServiceClient(),
) -> Mapping[str, str]:
    secrets = {}

    for key in keys:
        name = f"projects/cal-itp-data-infra/secrets/{key}/versions/latest"
        response = secret_client.access_secret_version(request={"name": name})

        crc32c = google_crc32c.Checksum()
        crc32c.update(response.payload.data)
        if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
            raise ValueError(f"Data corruption detected for secret {name}.")

        secrets[key] = response.payload.data.decode("UTF-8").strip()

    return secrets


if __name__ == "__main__":
    print("loading secrets...")
    print(get_secrets().keys())
