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

import unittest
from subprocess import check_output
from mock import patch
from ibm_storage_flocker_driver.lib.host_actions import (
    HostActions,
    PREFIX_DEVICE_PATH,
    MultipathDeviceNotFound,
    MultipathCmdNotFound,
    RescanCmdNotFound,
)

import logging

# Constants for unit testing
MULTIPATH_OUTPUT_WWN_MD = 'dm-0'
MULTIPATH_OUTPUT_WWN = '00173800fdf50f86'
WWN_PREFIX = '2'
MULTIPATH_OUTPUT_WWN_MD2 = 'dm-2'
MULTIPATH_OUTPUT_WWN2 = '2222222222222222'
MULTIPATH_OUTPUT = """
{}{} {} IBM     ,2810XIV
size=16G features='1 queue_if_no_path' hwhandler='0' wp=rw
`-+- policy='round-robin 0' prio=1 status=active
  |- 3:0:0:1 sdb 8:16 active ready running
    `- 4:0:0:1 sdc 8:32 active ready running
""".format(WWN_PREFIX, MULTIPATH_OUTPUT_WWN, MULTIPATH_OUTPUT_WWN_MD)

MULTIPATH_OUTPUT2 = MULTIPATH_OUTPUT + """
{}{} {} IBM     ,2810XIV
size=16G features='1 queue_if_no_path' hwhandler='0' wp=rw
`-+- policy='round-robin 0' prio=1 status=active
  |- 3:0:0:1 sdb 8:16 active ready running
    `- 4:0:0:1 sdc 8:32 active ready running
""".format(WWN_PREFIX, MULTIPATH_OUTPUT_WWN2, MULTIPATH_OUTPUT_WWN_MD2)

WWN_PREFIX2 = "3"
REDHAT_MULTIPATH_WWN = "6001738cfc9035e80000000000013aff"
REDHAT_MULTIPATH_MPATH = "mpathd"
REDHAT_MULTIPATH_OUTPUT = """
{mpath} ({prefix}{wwn}) dm-8 IBM     ,2810XIV
        size=75G features='1 queue_if_no_path' hwhandler='0' wp=rw
        `-+- policy='service-time 0' prio=1 status=enabled
          |- 3:0:0:1 sdb 8:16 active ready running
          `- 5:0:0:1 sdc 8:32 active ready running
""".format(mpath=REDHAT_MULTIPATH_MPATH, prefix=WWN_PREFIX2,
           wwn=REDHAT_MULTIPATH_WWN)


class TestHostActions(unittest.TestCase):
    """
    Unit testing for host actions module
    """

    @patch('ibm_storage_flocker_driver.lib.host_actions.check_output')
    @patch('ibm_storage_flocker_driver.lib.host_actions.os.path.exists')
    def test_get_multipath_device_exist_device(self, ospathexist,
                                               check_output_mock):
        check_output_mock.return_value = MULTIPATH_OUTPUT
        ospathexist.return_value = True
        hostops = HostActions()

        self.assertEqual(hostops.get_multipath_device(MULTIPATH_OUTPUT_WWN),
                         '{}/{}'.format(PREFIX_DEVICE_PATH,
                                        WWN_PREFIX + MULTIPATH_OUTPUT_WWN))

    @patch('ibm_storage_flocker_driver.lib.host_actions.check_output')
    @patch('ibm_storage_flocker_driver.lib.host_actions.os.path.exists')
    def test_get_multipath_device_redhat_exist_device(self, ospathexist,
                                                      check_output_mock):
        check_output_mock.return_value = REDHAT_MULTIPATH_OUTPUT
        ospathexist.return_value = True
        hostops = HostActions()
        self.assertEqual(hostops.get_multipath_device(REDHAT_MULTIPATH_WWN),
                         '{}/{}'.format(PREFIX_DEVICE_PATH,
                                        REDHAT_MULTIPATH_MPATH))

    @patch('ibm_storage_flocker_driver.lib.host_actions.check_output')
    @patch('ibm_storage_flocker_driver.lib.host_actions.os.path.exists')
    def test_get_multipath_device_exist2_device(self, ospathexist,
                                                check_output_mock):
        check_output_mock.return_value = MULTIPATH_OUTPUT2
        ospathexist.return_value = True
        hostops = HostActions()
        self.assertEqual(hostops.get_multipath_device(MULTIPATH_OUTPUT_WWN2),
                         '{}/{}'.format(PREFIX_DEVICE_PATH,
                                        WWN_PREFIX + MULTIPATH_OUTPUT_WWN2))

    @patch('ibm_storage_flocker_driver.lib.host_actions.check_output')
    @patch('ibm_storage_flocker_driver.lib.host_actions.os.path.exists')
    def test_get_multipath_device_not_exit_device(self, ospathexist,
                                                  check_output_mock):
        check_output_mock.return_value = MULTIPATH_OUTPUT
        ospathexist.return_value = True
        hostops = HostActions()
        self.assertRaises(MultipathDeviceNotFound,
                          hostops.get_multipath_device, 'fake-vol-wwn')

    @patch('ibm_storage_flocker_driver.lib.host_actions.check_output')
    def test_rescan(self, check_output_mock):
        check_output_mock.return_value = None
        hostops = HostActions()
        hostops.rescan_scsi()

    @patch('ibm_storage_flocker_driver.lib.host_actions.find_executable')
    def test_no_rescaan_cmd_exist(self, find_executable):
        find_executable.side_effect = [None, None]
        self.assertRaises(RescanCmdNotFound, HostActions)

    @patch('ibm_storage_flocker_driver.lib.host_actions.find_executable')
    def test_no_multipath_exist(self, find_executable):
        find_executable.side_effect = [None, 'rescan', 'iscsiadm', None]
        self.assertRaises(MultipathCmdNotFound, HostActions)
