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
from bitmath import GiB, MiB
from flocker.node.agents.test.test_blockdevice import (
    make_iblockdeviceapi_tests,
)
from testtools_ibm_storage_flocker_driver import \
    get_ibm_storage_blockdevice_api_for_test

# Smallest volume to create in tests
MIN_ALLOCATION_SIZE = int(GiB(1).to_Byte().value)

# Minimum unit of volume allocation
MIN_ALLOCATION_UNIT = int(MiB(1).to_Byte().value)


class IBMStorageBlockDeviceAPITests(
        make_iblockdeviceapi_tests(
            blockdevice_api_factory=(
                lambda test_case: get_ibm_storage_blockdevice_api_for_test(
                    uuid4(), test_case)
            ),
            minimum_allocatable_size=MIN_ALLOCATION_SIZE,
            device_allocation_unit=MIN_ALLOCATION_UNIT,
            unknown_blockdevice_id_factory=lambda test: unicode(uuid4())
        )
):
    """
    Basic interface tests for ``IBMStorageBlockDeviceAPITests``
    """
