#!/usr/bin/env python
# encoding: utf-8
"""
setup.py
"""

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import os
import pkgutil

MODNAME = "veezi"

def _read_version():
    with open(os.path.join(os.path.dirname(__file__), "version.txt"), "r") as version_file:
        return version_file.read().rstrip()

class NoseTestCommand(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import nose
        nose.run_exit(argv=['nosetests'])

setup(
    name = MODNAME,
    version = _read_version(),
    description = MODNAME,
    author = 'Kurtiss Hare',
    author_email = 'kurtiss@gmail.com',
    url = 'http://www.github.com/kurtiss/' + MODNAME,
    packages = find_packages('src'),
    package_data = {'' : ['version.txt']},
    package_dir = {'' : 'src'},
    scripts = [],
    classifiers = [
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    install_requires = [
        "requests==2.9.0",
        "beautifulsoup4==4.4.1",
        "et_xmlfile==1.0.1",
        "jdcal==1.2",
        "more-itertools==2.2",
        "openpyxl==2.3.2",
        "python-dateutil==2.4.2",
        # 'simplejson==3.7.3',
        "six==1.10.0",
        # 'wsgiref==0.1.2'
    ],
    tests_require = [
        "nose==1.3.7"
    ],
    cmdclass = dict(
        test = NoseTestCommand
    ),
    zip_safe = False
)
