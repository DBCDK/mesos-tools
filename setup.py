#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- mode: python -*-
from setuptools import setup, find_packages
import glob

## See the following pages for keywords possibilities for setup keywords, etc.
# https://packaging.python.org/
# https://docs.python.org/3/distutils/apiref.html
# https://docs.python.org/3/distutils/setupscript.html

setup(name='mesos-tools',
      version='0.1.0',
      package_dir={'': 'src'},
      packages=find_packages(where='src'),
      description='Basic utilities used in mesos/marathon deployment',
      scripts=glob.glob('src/bin/*'),
      test_suite='..tests',
      install_requires=['requests'],
      provides=['mesos_tools'],
      maintainer="jda",
      maintainer_email="jda@dbc.dk",
      zip_safe=False)
