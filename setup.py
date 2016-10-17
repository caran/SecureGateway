#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

# Read version string. See
# http://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package
exec(open('sgframework/version.py').read())

setup(
    name='sgframework',
    version=__version__,
    description="A framework for the Secure Gateway concept architecture.",
    long_description=readme + '\n\n' + history,
    author="Jonas Berg",
    author_email='caranopensource@semcon.com',
    url='https://github.com/caran/SecureGateway',
    packages=['sgframework'],
    package_dir={'sgframework': 'sgframework'},
    scripts=['scripts/canadapter', 'scripts/servicemanager', 'scripts/canadapterlib.py'],
    include_package_data=True,
    install_requires=['can4python', 'paho-mqtt'],
    license="BSD",
    zip_safe=False,
    keywords='sgframework',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Hardware :: Hardware Drivers'
    ],
    test_suite='tests.suites.embedded',
    tests_require=[]
)
