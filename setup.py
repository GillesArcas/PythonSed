#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import re
import shutil
import glob
import codecs
from setuptools import setup, find_packages


def read(*parts):
    here = os.path.abspath(os.path.dirname(__file__))
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with codecs.open(os.path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^VERSION = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


if __name__ == "__main__":

    try:
        shutil.copytree('tests', r'PythonSed\tests')

        test_files = []
        for path, subdirs, files in os.walk(r'PythonSed\tests'):
            for name in files:
                test_files.append(os.path.join(path, name))
        data_files=[
        # ('Lib/site-packages/PythonSed', ['README.md', 'LICENSE'] + glob.glob('tests/*.*')),
        ('tests', test_files)
        ]

        setup(
            name='PythonSed',
            version=find_version("PythonSed", "sed.py"),
            license='MIT',
            url='https://github.com/GillesArcas/PythonSed',
            author='Gilles Arcas',
            author_email='gilles.arcas@gmail.com',
            description='Full and working implementation of sed in python\n',
            packages=find_packages(),
            entry_points={
                'console_scripts': ['pythonsed = PythonSed.sed:main']
            },
            zip_safe=True,
            include_package_data=True,
            data_files=data_files
            #package_data=data_files
            #package_data={'test': ['tests/testsuite1/*.*', ]}
        )

    finally:
        shutil.rmtree(r'PythonSed\tests')
