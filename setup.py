#!/usr/bin/env python

import re
import ast
from setuptools import setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('calitp.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    name='calitp',
    version=version,
    py_modules=['calitp'],
    install_requires=[
        ],
    description='',
    author='',
    author_email='',
    url='https://github.com/cal-itp/calitp-py'
    )

