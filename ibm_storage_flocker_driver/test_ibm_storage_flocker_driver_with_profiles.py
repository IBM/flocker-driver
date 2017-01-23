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

from uuid import uuid4
from bitmath import GiB

from flocker.node.agents.test.test_blockdevice import (
    make_iprofiledblockdeviceapi_tests,
)
from ibm_storage_flocker_driver.testtools_ibm_storage_flocker_driver import \
    get_ibm_storage_blockdevice_api_for_test

MIN_ALLOCATION_SIZE = int(GiB(1).to_Byte().value)


class IBMStorageIProfiledBlockDeviceAPITestsMixin(
        make_iprofiledblockdeviceapi_tests(
            profiled_blockdevice_api_factory=(
                lambda test_case: get_ibm_storage_blockdevice_api_for_test(
                    uuid4(), test_case)
            ),
            dataset_size=MIN_ALLOCATION_SIZE
        )
):
    """
    Interface profile tests for ``IBMStorageIProfiledBlockDeviceAPITestsMixin``

    Important:
    IBM Storage plug-in for Flocker does not require Gold, Silver and
    Bronze profiles.
    You can define any profile that matches the storage service name within
    the IBM Spectrum Control Base Edition (SCBE).
    However, to run this test, Gold, Silver and Bronze
    storage services must be defined and delegated to the Flocker interface
    on SCBE.
    """
