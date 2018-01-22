#!/usr/bin/env python
import uuid

try:
    from setuptools import find_packages, setup
except ImportError:
    from distutils.core import setup

from pip.req import parse_requirements

install_reqs = parse_requirements('requirements.txt', session=uuid.uuid1())
reqs = [str(ir.req) for ir in install_reqs]


__author__ = 'dbarrosop@dravetech.com'
__license__ = 'Apache License, version 2'

__version__ = '0.0.6'

setup(name='brigade',
      version=__version__,
      description="Fighting fire with fire",
      author=__author__,
      url='https://github.com/napalm-automation/brigade',
      include_package_data=True,
      install_requires=reqs,
      packages=find_packages(exclude=("test*", )),
      license=__license__,
      test_suite='tests',
      platforms='any',
      classifiers=['Development Status :: 4 - Beta',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.4',
                   'Programming Language :: Python :: 3.5',
                   'Programming Language :: Python :: 3.6',
                   ])
