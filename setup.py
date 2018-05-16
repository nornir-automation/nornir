#!/usr/bin/env python
from setuptools import find_packages, setup

with open("requirements.txt", "r") as fs:
    reqs = [r for r in fs.read().splitlines() if (len(r) > 0 and not r.startswith("#"))]

with open("README.md", "r") as fs:
    long_description = fs.read()

__author__ = "dbarrosop@dravetech.com"
__license__ = "Apache License, version 2"

__version__ = "1.0.1"

setup(
    name="nornir",
    version=__version__,
    description="Fighting fire with fire",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=__author__,
    url="https://github.com/nornir-automation/nornir",
    include_package_data=True,
    install_requires=reqs,
    packages=find_packages(exclude=("test*",)),
    license=__license__,
    test_suite="tests",
    platforms="any",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
)
