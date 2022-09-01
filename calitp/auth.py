import os
from typing import Sequence

import google_crc32c
from google.cloud import secretmanager

AUTH_KEYS_ENV_VAR = "CALITP_AUTH_KEYS"
if AUTH_KEYS_ENV_VAR in os.environ:
    DEFAULT_AUTH_KEYS = tuple(os.environ[AUTH_KEYS_ENV_VAR].split(","))
else:
    DEFAULT_AUTH_KEYS = (
        "AC_TRANSIT_API_KEY",
        "AMTRAK_GTFS_URL",
        "CULVER_CITY_API_KEY",
        "MTC_511_API_KEY",
        "SD_MTS_SA_API_KEY",
        "SD_MTS_VP_TU_API_KEY",
        "SWIFTLY_AUTHORIZATION_KEY_CALITP",
        "WEHO_RT_KEY",
    )


def load_secrets(keys: Sequence[str] = DEFAULT_AUTH_KEYS, secret_client=secretmanager.SecretManagerServiceClient()):
    for key in keys:
        if key not in os.environ:
            print(f"fetching secret {key}")
            name = f"projects/cal-itp-data-infra/secrets/{key}/versions/latest"
            response = secret_client.access_secret_version(request={"name": name})

            crc32c = google_crc32c.Checksum()
            crc32c.update(response.payload.data)
            if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
                raise ValueError(f"Data corruption detected for secret {name}.")

            os.environ[key] = response.payload.data.decode("UTF-8").strip()
