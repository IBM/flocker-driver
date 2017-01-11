##############################################################################
# Copyright 2016 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##############################################################################

from ibm_storage_flocker_driver.lib.messages import (
    PACKAGE_FORMAL_DESCRIPTION,
    PACKAGE_FORMAL_KEYWORDS,
)
from setuptools import setup, find_packages
import codecs  # To use a consistent encoding

with codecs.open('DESCRIPTION.rst', encoding='utf-8') as description:
    long_description = description.read()

with open("requirements.txt") as requirements:
    install_requires = requirements.readlines()

setup(
    name='ibm_storage_flocker_driver',
    version='1.0.0',
    description=PACKAGE_FORMAL_DESCRIPTION,
    long_description=long_description,
    author='Shay Berman',
    author_email='bshay@il.ibm.com',
    url='https://github.com/ibm/flocker_driver',
    license='Apache 2.0',

    classifiers=[
        'Development Status :: Beta',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ],

    keywords=PACKAGE_FORMAL_KEYWORDS,
    packages=find_packages(exclude=['test*']),
    install_requires=install_requires,
    data_files=[('/etc/flocker/', ['conf/template_agent.yml'])]
)
