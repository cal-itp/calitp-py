#!/usr/bin/env python

import re
import ast
from setuptools import setup, find_namespace_packages

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("calitp/__init__.py", "rb") as f:
    version = str(
        ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1))
    )

setup(
    name="calitp",
    version=version,
    packages=find_namespace_packages(),
    install_requires=[
        "gcsfs",
        "pandas",
        "pandas-gbq",
        "pybigquery",
        "google-cloud-bigquery",
    ],
    description="",
    author="",
    author_email="",
    url="https://github.com/cal-itp/calitp-py",
)
