#!/usr/bin/env python

import ast
import re

from setuptools import find_namespace_packages, setup

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("calitp_py/__init__.py", "rb") as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1)))

setup(
    name="calitp",
    version=version,
    packages=find_namespace_packages(),
    install_requires=[
        "gcsfs",
        "pandas",
        "pandas-gbq",
        "sqlalchemy-bigquery",
        "google-cloud-bigquery",
        "gtfs-realtime-bindings",
    ],
    description="",
    author="",
    author_email="",
    url="https://github.com/cal-itp/calitp-py",
)
