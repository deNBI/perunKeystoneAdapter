#!/usr/bin/env python
# encoding: utf-8
import os
from setuptools import find_packages, setup
import pkg_resources

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

def dependencies():
    file_ = pkg_resources.resource_filename(__name__, os.path.join('requirements', 'default.txt'))
    with open(file_, 'r') as f:
        return f.read().splitlines()

setup(
    name='perunKeystoneAdapter',
    version='0.2',
    packages=find_packages(),
    include_package_data=True,
    license='Apache License 2.0',
    description='The Perun Keystone Adapter is a library written in Python that parses data propagated by Perun and modifies a connected Openstack Keystone.',
    long_description=README,
    author='Jan Krüger',
    install_requires=dependencies(),
    entry_points='''
        [console_scripts]
        perun_propagation=denbi.scripts.perun_propagation:main
        perun_propagation_service=denbi.scripts.perun_propagation_service:main
        perun_set_project_flag=denbi.scripts.set_project_flag:main
        perun_set_user_flag=denbi.scripts.set_user_flag:main
    ''',
    classifiers=[
        'Environment :: OpenStack'
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)
