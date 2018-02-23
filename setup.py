import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='perunKeystoneAdapter',
    version='0.1',
    packages=find_packages('python'),
    include_package_data=True,
    license='Apache License 2.0', 
    description='The Perun Keystone Adapter is a library written in Python that parses data propagated by Perun and modifies a connected Openstack Keystone.',
    long_description=README,
    author='Jan Krüger',
    install_requires = requirements,
    classifiers=[
        'Environment :: OpenStack'
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
