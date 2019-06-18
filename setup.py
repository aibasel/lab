#! /usr/bin/env python

from setuptools import setup

from lab import __version__ as version


setup(
    name='Lab',
    version=version.rstrip('+'),
    description='Benchmark your code',
    long_description='\n\n'.join(
        [open('README.rst').read()]),
    keywords='benchmarks cluster grid',
    author='Jendrik Seipp',
    author_email='jendrikseipp@gmail.com',
    url='https://bitbucket.org/jendrikseipp/lab',
    license='GPL3+',
    packages=[
        'downward', 'downward.reports',
        'lab', 'lab.calls', 'lab.external', 'lab.reports'],
    package_data={
        'downward': ['scripts/*.py'],
        'lab': ['data/*', 'scripts/*.py']},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    entry_points={
    },
    install_requires=[
        'matplotlib',
        'simplejson',
    ],
)
