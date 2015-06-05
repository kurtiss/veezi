#!/usr/bin/env python
# encoding: utf-8
"""
setup.py
"""

from setuptools import setup, find_packages
import os

MODNAME = "veezi"

execfile(os.path.join('src', MODNAME, 'version.py'))

setup(
    name = MODNAME,
    version = VERSION,
    description = MODNAME,
    author = 'Kurtiss Hare',
    author_email = 'kurtiss@gmail.com',
    url = 'http://www.github.com/kurtiss/' + MODNAME,
    packages = find_packages('src'),
    package_dir = {'' : 'src'},
    scripts = [
        'src/scripts/fourboxdsync'
    ],
    classifiers = [
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    install_requires = [
    ],
    zip_safe = False
)