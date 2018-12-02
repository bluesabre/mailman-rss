#!/usr/bin/env python
from setuptools import setup
import os
import sys

def get_version():
    curdir = os.path.dirname(__file__)
    filename = os.path.join(curdir, 'src', 'mailman_rss', 'version.py')
    with open(filename, 'rb') as fp:
        return fp.read().decode('utf8').split('=')[1].strip(' \n"')


def readme(filename):
    with open(filename, 'r') as f:
        return f.read()


setup(
    name='mailman-rss',
    version=get_version(),
    description='Scrape mailman archive and convert to rss',
    long_description=readme('README.rst'),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Communications :: Email',
    ],
    keywords='mailman rss',
    url='https://github.com/kyamagu/mailman_rss',
    author='Kota Yamaguchi',
    author_email='KotaYamaguchi1984@gmail.com',
    license='MIT License',
    package_dir={'': 'src'},
    packages=['mailman_rss'],
    install_requires=[
        'beautifulsoup4',
        'python-dateutil',
        'future',
        'requests',
    ],
    extras_require={
        'twitter': 'python-twitter',
    },
    include_package_data=True,
    entry_points={
        'console_scripts': ['mailman-rss=mailman_rss.__main__:main']
    },
    tests_require=['unittest'],
    )
