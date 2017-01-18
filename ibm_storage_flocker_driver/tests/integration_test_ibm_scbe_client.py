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
from nose.plugins.attrib import attr
import os
from ibm_storage_flocker_driver.lib.abstract_client import ConnectionInfo
from ibm_storage_flocker_driver.lib import ibm_scbe_client
from ibm_storage_flocker_driver.lib.constants import DEFAULT_DEBUG_LEVEL

ENV_SCBE_IP = 'SCBE_IP'
ENV_SCBE_USER = 'SCBE_USER'
ENV_SCBE_PASSWORD = 'SCBE_PASSWORD'
ENV_SCBE_SERVICE = 'SCBE_SERVICE'
ENV_HOST_DEFINED = 'HOST_DEFINE'
MANDATORIES_ENV = [
    ENV_SCBE_IP, ENV_SCBE_USER, ENV_SCBE_PASSWORD,
    ENV_SCBE_SERVICE, ENV_HOST_DEFINED,
]


class IntegrationTestSCBEClient(unittest.TestCase):
    """
    ibm_scbe_client integration test case.
    You need SCBE up and running in order to run this integration test.
    All the ENV_SCBE_* env is mandatory in order to run this integration test.
    """
    def setUp(self):
        for env in MANDATORIES_ENV:
            if env not in os.environ:
                raise Exception('env {} is mandatory'.format(env))

    @attr('integration')
    def integ_test_basic_flow(self):
        con_info = ConnectionInfo(
            os.environ[ENV_SCBE_IP],
            os.environ[ENV_SCBE_USER],
            os.environ[ENV_SCBE_PASSWORD],
            debug_level=DEFAULT_DEBUG_LEVEL,
        )
        c = ibm_scbe_client.IBMSCBEClientAPI(con_info)

        host = os.environ[ENV_HOST_DEFINED]
        service = os.environ[ENV_SCBE_SERVICE]
        volname = "shay"

        self.assertEqual(c.allocation_unit(), 1024 * 1024)
        self.assertTrue(service in c.list_service_names())
        self.assertTrue(c.resource_exists(service))

        vol_size = 1024 * 1024 * 10
        self.vol = c.create_volume(
            vol=volname, resource=service, size=vol_size)
        vols = [i for i in c.list_volumes() if i.wwn == self.vol.wwn]
        self.assertEqual(len(vols), 1)

        c.map_volume(self.vol.wwn, host)
        self.assertEqual(c.get_vol_mapping(self.vol.wwn), host)

        c.unmap_volume(self.vol.wwn, host)
        self.assertEqual(c.get_vol_mapping(self.vol.wwn), None)

        c.delete_volume(self.vol.wwn)
        vols = [i for i in c.list_volumes() if i.wwn == self.vol.wwn]
        self.assertEqual(len(vols), 0)
