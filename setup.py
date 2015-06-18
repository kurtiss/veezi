#!/usr/bin/env python
# encoding: utf-8
"""
setup.py
"""

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import os

MODNAME = "veezi"
execfile(os.path.join('src', MODNAME, 'version.py'))


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
    version = VERSION,
    description = MODNAME,
    author = 'Kurtiss Hare',
    author_email = 'kurtiss@gmail.com',
    url = 'http://www.github.com/kurtiss/' + MODNAME,
    packages = find_packages('src'),
    package_dir = {'' : 'src'},
    scripts = [
        ''
    ],
    classifiers = [
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    install_requires = [
        'beautifulsoup4==4.3.2',
        'enum34==1.0.4',
        'jdcal==1.0',
        'more-itertools==2.2',
        'openpyxl==2.2.3',
        'python-dateutil==2.4.2',
        'requests==2.7.0',
        'simplejson==3.7.3',
        'six==1.9.0',
        'wsgiref==0.1.2'
    ],
    tests_require = [
        'nose==1.3.7'
    ],
    cmdclass = dict(
        test = NoseTestCommand
    ),
    zip_safe = False
)