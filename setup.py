#! /usr/bin/env python

from setuptools import setup

from lab import __version__ as version


with open("README.rst") as f1, open("INSTALL.rst") as f2:
    long_description = f1.read() + "\n\n" + f2.read()


setup(
    name="lab",
    version=version.rstrip("+"),
    description="Benchmark your code",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    keywords="benchmarks cluster grid",
    author="Jendrik Seipp",
    author_email="jendrikseipp@gmail.com",
    url="https://github.com/aibasel/lab",
    license="GPL3+",
    packages=["downward", "downward.reports", "lab", "lab.calls", "lab.reports"],
    package_data={"downward": ["scripts/*.py"], "lab": ["data/*", "scripts/*.py"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering",
    ],
    install_requires=[
        "matplotlib",  # for scatter plots
        "simplejson",  # optional, speeds up reading properties files
        "txt2tags>=3.6",  # for HTML and Latex reports
    ],
    python_requires=">=3.7",
)
