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
import socket
from mock import patch, MagicMock, Mock
from ibm_storage_flocker_driver import ibm_storage_blockdevice as driver

from uuid import UUID
from flocker.node.agents.blockdevice import (
    BlockDeviceVolume,
    UnknownVolume,
    UnattachedVolume,
    AlreadyAttachedVolume,
)
from bitmath import GiB
from ibm_storage_flocker_driver.tests import test_host_actions
from twisted.python.filepath import FilePath
from ibm_storage_flocker_driver.lib.host_actions import (
    PREFIX_DEVICE_PATH,
)
from ibm_storage_flocker_driver.lib.abstract_client import ConnectionInfo
from ibm_storage_flocker_driver.lib.abstract_client import VolInfo
from ibm_storage_flocker_driver.lib.abstract_client import (
    FactoryBackendAPIClient,
    IBMDriverNoClientModuleFound,
)
from ibm_storage_flocker_driver.lib.constants import DEFAULT_DEBUG_LEVEL
from ibm_storage_flocker_driver.lib import messages

# Constants for unit testing
UUID1_STR = '737d4ea0-28bf-11e6-b12e-68f7288f1809'
UUID1_SLUG = 'c31OoCi_EeaxLmj3KI8YCQ'
UUID2_SLUG_FAKE = 'xxxxxxxxxxxxxxxxxxxxxx'
UUID3_STR = '737d4ea0-28bf-11e6-b12e-eeeeeeeeeeee'

VOL_NAME = '{}{}_{}'.format(
    driver.VOL_NAME_FLOCKER_PREFIX,
    UUID1_STR,
    UUID1_SLUG,
)
VOL_NAME_WITH_FAKE_CLUSTER_ID = '{}{}_{}'.format(
    driver.VOL_NAME_FLOCKER_PREFIX,
    UUID1_STR,
    UUID2_SLUG_FAKE,
)

BDV1 = BlockDeviceVolume(
    blockdevice_id=unicode(UUID1_STR),
    size=int(GiB(16).to_Byte().value),
    attached_to=None,
    dataset_id=UUID(UUID1_STR)
)

BDV3 = BlockDeviceVolume(
    blockdevice_id=unicode(UUID3_STR),
    size=int(GiB(32).to_Byte().value),
    attached_to=None,
    dataset_id=UUID(UUID3_STR)
)

IS_MULTIPATH_EXIST = 'ibm_storage_flocker_driver.lib.host_actions.' \
                     'HostActions.is_multipath_active'
LIST_VOLUMES = 'ibm_storage_flocker_driver.ibm_storage_blockdevice.' \
               'IBMStorageBlockDeviceAPI.list_volumes'

CONF_INFO_MOCK = MagicMock()
CONF_INFO_MOCK.debug_level = DEFAULT_DEBUG_LEVEL
CONF_INFO_MOCK.con_info.credential = dict(username='fake')


class TestBlockDeviceBasicModuleFuncs(unittest.TestCase):
    """
    Unit testing for basic funcs of the module
    """

    def test_uuid2slug(self):
        slug = driver.uuid2slug(UUID1_STR)
        self.assertEqual(slug, UUID1_SLUG)

    def test_slug2uuid(self):
        uuid = driver.slug2uuid(UUID1_SLUG)
        self.assertEqual(uuid, UUID1_STR)

    def test_get_dataset_id_from_vol_name(self):
        dataset_id = driver.get_dataset_id_from_vol_name(VOL_NAME)
        self.assertEqual(dataset_id, UUID(UUID1_STR))

    def test_get_cluster_id_slug_from_vol_name(self):
        slug = driver.get_cluster_id_slug_from_vol_name(VOL_NAME)
        self.assertEqual(slug, UUID1_SLUG)

    def test_build_vol_name(self):
        volname = driver.build_vol_name(UUID1_STR, UUID1_SLUG)
        self.assertEqual(volname, VOL_NAME)

    def test_get_blockdevicevolume(self):
        size = int(GiB(16).to_Byte().value)
        blockdevicevol = driver._get_blockdevicevolume(
            UUID(UUID1_STR),
            test_host_actions.MULTIPATH_OUTPUT_WWN,
            size,
            attached_to=None,
        )
        expacted_blockdevicevolume = BlockDeviceVolume(
            blockdevice_id=unicode(test_host_actions.MULTIPATH_OUTPUT_WWN),
            size=size,
            attached_to=None,
            dataset_id=UUID(UUID1_STR),
        )
        self.assertEqual(blockdevicevol, expacted_blockdevicevolume)


class TestBlockDevice(unittest.TestCase):
    """
    Unit testing for IBMStorageBlockDeviceAPI Class
    """

    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_client.con_info = CONF_INFO_MOCK
        self.mock_client.backend_type = messages.SCBE_STRING

    @patch(IS_MULTIPATH_EXIST)
    def test_IBMStorageBlockDeviceAPI_init(self, check_output_mock):
        check_output_mock.return_value = True
        driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, self.mock_client, 'fakepool')
        self.assertEqual(driver_obj._client, self.mock_client)
        self.assertEqual(driver_obj._cluster_id, UUID1_STR)
        self.assertEqual(driver_obj._storage_resource, 'fakepool')
        self.assertEqual(driver_obj._instance_id, socket.gethostname())
        self.assertEqual(driver_obj._cluster_id_slug, UUID1_SLUG)
        self.assertEqual(driver_obj._is_multipathing, True)

    @patch(IS_MULTIPATH_EXIST)
    def test_IBMStorageBlockDeviceAPI_is_cluster_volume(
            self, check_output_mock):
        check_output_mock.return_value = True
        driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, self.mock_client, 'fakepool')
        self.assertTrue(driver_obj._is_cluster_volume(VOL_NAME))
        self.assertFalse(driver_obj._is_cluster_volume(
            VOL_NAME_WITH_FAKE_CLUSTER_ID))

    @patch(IS_MULTIPATH_EXIST)
    def test_IBMStorageBlockDeviceAPI_get_volume(
            self, multipathing_mock):
        multipathing_mock.return_value = True
        fake_vol_list = [BDV1, BDV3]
        self.mock_client.list_volumes = MagicMock(return_value=fake_vol_list)
        driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, self.mock_client, 'fakepool')

        driver_obj._get_blockdevicevolume_by_vol = MagicMock(return_value=BDV1)
        self.assertTrue(driver_obj._get_volume(unicode(UUID1_STR)), BDV1)

        driver_obj._get_blockdevicevolume_by_vol = MagicMock(return_value=BDV3)
        self.assertTrue(driver_obj._get_volume(unicode(UUID3_STR)), BDV3)

        self.mock_client.list_volumes = MagicMock(return_value=[])
        self.assertRaises(UnknownVolume, driver_obj._get_volume,
                          unicode('fack-lockdevice-id'))

    @patch(IS_MULTIPATH_EXIST)
    def test_IBMStorageBlockDeviceAPI_volume_exist(self, multipathing_mock):
        multipathing_mock.return_value = True
        fake_vol_list = [BDV1, BDV3]

        self.mock_client.list_volumes = MagicMock(return_value=fake_vol_list)
        self.mock_client.con_info = CONF_INFO_MOCK
        driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, self.mock_client, 'fakepool')
        driver_obj._get_blockdevicevolume_by_vol = MagicMock(return_value=BDV1)
        self.assertTrue(driver_obj._volume_exist(unicode(UUID1_STR)))

        driver_obj._get_blockdevicevolume_by_vol = MagicMock(return_value=BDV1)
        self.assertTrue(driver_obj._volume_exist(unicode(UUID3_STR)))

        self.mock_client.list_volumes = MagicMock(return_value=[])
        self.assertFalse(
            driver_obj._volume_exist(unicode('fack-lockdevice-id')))

    @patch(IS_MULTIPATH_EXIST)
    def test_IBMStorageBlockDeviceAPI_create_volume(self, multipathing_mock):
        size = int(GiB(16).to_Byte().value)
        multipathing_mock.return_value = True
        mock_vol_obj = MagicMock
        mock_vol_obj.id = 'vol-id-11111'
        mock_vol_obj.size = size
        mock_vol_obj.name = 'volfack'
        mock_vol_obj.wwn = '11111111111'

        self.mock_client.list_volumes = MagicMock(
            return_value=[mock_vol_obj])
        self.mock_client.create_volume = MagicMock
        self.mock_client.handle_default_pool = MagicMock
        self.mock_client.handle_default_profile = MagicMock(
            return_value='fakepool')
        self.mock_client.con_info = CONF_INFO_MOCK

        driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, self.mock_client, 'fakepool')

        bdv = driver_obj.create_volume(UUID(UUID1_STR),
                                       GiB(size).to_Byte().value)

        expacted_blockdevicevolume = BlockDeviceVolume(
            blockdevice_id=unicode(mock_vol_obj.wwn),
            size=size,
            attached_to=None,
            dataset_id=UUID(UUID1_STR),
        )
        self.assertEqual(bdv, expacted_blockdevicevolume)

    @patch('ibm_storage_flocker_driver.lib.host_actions.check_output')
    @patch(IS_MULTIPATH_EXIST)
    @patch('ibm_storage_flocker_driver.lib.host_actions.os.path.exists')
    def test_IBMStorageBlockDeviceAPI_get_device_path(
            self, ospathexist, multipathing_mock, check_output_mock):
        multipathing_mock.return_value = True
        ospathexist.return_value = True
        check_output_mock.return_value = test_host_actions.MULTIPATH_OUTPUT2

        blockdevicevolume = BlockDeviceVolume(
            blockdevice_id=unicode(test_host_actions.MULTIPATH_OUTPUT_WWN2),
            size=int(GiB(16).to_Byte().value),
            attached_to=u'fakehost',
            dataset_id=UUID(UUID1_STR),
        )
        driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, self.mock_client, 'fakepool')

        class VolInfoFake(object):
            name = 'fake_volname'
        driver_obj._get_volume_object = MagicMock(return_value=VolInfoFake())
        driver_obj._get_blockdevicevolume_by_vol = MagicMock(
            return_value=blockdevicevolume)
        self.mock_client.backend_type = 'XIV'

        class r_list():

            def __init__(self, wwn):
                pass
            name = UUID1_STR
        self.mock_client.list_volumes = MagicMock(return_value=[r_list])

        dpath = driver_obj.get_device_path(blockdevicevolume.blockdevice_id)
        self.assertEqual(
            dpath,
            FilePath('{}/{}'.format(
                PREFIX_DEVICE_PATH,
                test_host_actions.WWN_PREFIX +
                test_host_actions.MULTIPATH_OUTPUT_WWN2,
            )))

    @patch('ibm_storage_flocker_driver.lib.host_actions.check_output')
    @patch(IS_MULTIPATH_EXIST)
    def test_IBMStorageBlockDeviceAPI_get_device_path_not_found(
            self, multipathing_mock, check_output_mock):
        multipathing_mock.return_value = True
        check_output_mock.return_value = test_host_actions.MULTIPATH_OUTPUT2

        blockdevicevolume = BlockDeviceVolume(
            blockdevice_id=unicode(UUID1_STR),
            size=int(GiB(16).to_Byte().value),
            attached_to=u'fakehost',
            dataset_id=UUID(UUID1_STR),
        )
        driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, self.mock_client, 'fakepool')

        class VolInfoFake(object):
            name = 'fake_volname'
        driver_obj._get_volume_object = MagicMock(return_value=VolInfoFake())
        driver_obj._get_blockdevicevolume_by_vol = MagicMock(
            return_value=blockdevicevolume)
        self.assertRaises(UnattachedVolume, driver_obj.get_device_path,
                          blockdevicevolume.blockdevice_id)

    @patch(IS_MULTIPATH_EXIST)
    def test_IBMStorageBlockDeviceAPI_get_device_path_not_attached_vol(
            self, multipathing_mock):
        size = 16
        multipathing_mock.return_value = True

        blockdevicevolume = BlockDeviceVolume(
            blockdevice_id=unicode(UUID1_STR),
            size=int(GiB(16).to_Byte().value),
            attached_to=None,
            dataset_id=UUID(UUID1_STR),
        )

        class ResultList():

            def __init__(self, wwn):
                pass
            name = UUID1_STR
        self.mock_client.list_volumes = MagicMock(return_value=[ResultList])
        driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, self.mock_client, 'fakepool')

        class VolInfoFake(object):
            name = 'fake_volname'
        driver_obj._get_volume_object = MagicMock(return_value=VolInfoFake())
        driver_obj._get_blockdevicevolume_by_vol = MagicMock(
            return_value=blockdevicevolume)
        self.assertRaises(UnattachedVolume, driver_obj.get_device_path,
                          blockdevicevolume.blockdevice_id)

    @patch(IS_MULTIPATH_EXIST)
    def test_IBMStorageBlockDeviceAPI_get_blockdevicevolume_by_vol(
            self, multipathing_mock):

        multipathing_mock.return_value = True
        FAKE_CLUSTER_ID = UUID1_STR
        vol_info = VolInfo('f_{}_{}'.format(UUID1_STR, UUID1_SLUG),
                           int(GiB(16).to_Byte().value),
                           1111,
                           UUID1_STR)
        blockdevicevolume = BlockDeviceVolume(
            blockdevice_id=unicode(UUID1_STR),
            size=int(GiB(16).to_Byte().value),
            attached_to=u'fake_host',
            dataset_id=UUID(UUID1_STR),
        )

        self.mock_client.get_vol_mapping = MagicMock(return_value='fake_host')
        driver_obj = driver.IBMStorageBlockDeviceAPI(
            FAKE_CLUSTER_ID, self.mock_client, 'fakepool')
        driver_obj._is_cluster_volume = MagicMock(return_value=False)
        self.assertRaises(
            UnknownVolume,
            driver_obj._get_blockdevicevolume_by_vol,
            vol_info)

        driver_obj._is_cluster_volume = MagicMock(return_value=True)
        self.assertEqual(blockdevicevolume,
                         driver_obj._get_blockdevicevolume_by_vol(vol_info))

    def test_IBMStorageBlockDeviceAPI_destroy_volume_not_exist(self):
        self.mock_client.list_volumes = MagicMock(return_value=[])
        driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, self.mock_client, 'fakepool')

        self.assertRaises(UnknownVolume, driver_obj.destroy_volume,
                          unicode(UUID(UUID1_STR)))

    def test_IBMStorageBlockDeviceAPI_destroy_volume_exist(self):
        self.mock_client.delete_volume = Mock()
        driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, self.mock_client, 'fakepool')
        expacted_blockdevicevolume = BlockDeviceVolume(
            blockdevice_id=unicode('999'),
            size=10,
            attached_to=None,
            dataset_id=UUID(UUID1_STR),
        )
        driver_obj._get_volume = \
            MagicMock(return_value=expacted_blockdevicevolume)

        driver_obj.destroy_volume(unicode(UUID(UUID1_STR)))


class TestBlockDeviceAttachDetach(unittest.TestCase):
    """
    Unit testing for IBMStorageBlockDeviceAPI Class attach detach methods
    """

    def setUp(self):
        self.mock_client = MagicMock
        self.mock_client.con_info = CONF_INFO_MOCK
        self.mock_client.backend_type = messages.SCBE_STRING

        self.mock_client.map_volume = MagicMock()
        self.mock_client.unmap_volume = MagicMock()
        self.driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, self.mock_client, 'fakepool')
        self.driver_obj._host_ops.rescan_scsi = MagicMock()

        self.expacted_blockdevicevolume = BlockDeviceVolume(
            blockdevice_id=unicode('999'),
            size=10,
            attached_to=None,
            dataset_id=UUID(UUID1_STR),
        )

    def test_IBMStorageBlockDeviceAPI_attach_volume_already_attached(self):
        self.expacted_blockdevicevolume = \
            self.expacted_blockdevicevolume.set(attached_to=u'fake-host')
        self.driver_obj._get_volume = \
            MagicMock(return_value=self.expacted_blockdevicevolume)
        self.driver_obj._get_volume = \
            MagicMock(return_value=self.expacted_blockdevicevolume)

        self.assertRaises(
            AlreadyAttachedVolume, self.driver_obj.attach_volume,
            unicode(UUID1_STR), 'fake-host')

    def test_IBMStorageBlockDeviceAPI_attach_volume_succeed(self):
        self.expacted_blockdevicevolume = \
            self.expacted_blockdevicevolume.set(attached_to=None)
        self.driver_obj._get_volume = \
            MagicMock(return_value=self.expacted_blockdevicevolume)

        attached_to = self.driver_obj.attach_volume(
            unicode(UUID1_STR), u'fake-host').attached_to
        self.assertEqual(attached_to, 'fake-host')

    def test_IBMStorageBlockDeviceAPI_attach_volume_already_detached(self):
        self.expacted_blockdevicevolume = \
            self.expacted_blockdevicevolume.set(attached_to=None)
        self.driver_obj._get_volume = \
            MagicMock(return_value=self.expacted_blockdevicevolume)
        self.driver_obj._get_volume = \
            MagicMock(return_value=self.expacted_blockdevicevolume)

        self.assertRaises(
            UnattachedVolume, self.driver_obj.detach_volume,
            unicode(UUID1_STR))

    def test_IBMStorageBlockDeviceAPI_detach_volume_succeed(self):
        self.expacted_blockdevicevolume = \
            self.expacted_blockdevicevolume.set(attached_to=u'fake-host')
        self.driver_obj._get_volume = \
            MagicMock(return_value=self.expacted_blockdevicevolume)
        self.driver_obj._clean_up_device_before_unmap = Mock()

        self.assertEqual(
            None,
            self.driver_obj.detach_volume(unicode(UUID1_STR)))


WWN1 = '6001738CFC9035E80000000000014A81'
WWN2 = '6001738CFC9035E80000000000014A82'
WWN1_SIZE = 1073741824
WWN2_SIZE = 1073741825
HOST = 'docker-host1'
HOST_ID = 45
class TestBlockDeviceVolumeList(unittest.TestCase):
    """
    Unit testing for IBMStorageBlockDeviceAPI focus on volume_list function.
    """

    @patch(IS_MULTIPATH_EXIST)
    def setUp(self, multipathing_mock):
        multipathing_mock.return_value = True

        self.list_volumes_fake = [
            VolInfo('f_{}_{}'.format(UUID1_STR, UUID1_SLUG),
                    WWN1_SIZE, '28d4e218f01647', WWN1),
            VolInfo('f_{}_{}'.format(UUID3_STR, UUID1_SLUG),
                    WWN2_SIZE, '28d4e218f01647', WWN2),
            # and one with different clusterid
            VolInfo('f_{}_{}'.format(UUID3_STR, '666'),
                    WWN2_SIZE, '28d4e218f01647', WWN2),
        ]
        self.get_vols_mapping_fake = {WWN1: HOST_ID, WWN2: HOST_ID}
        self.get_hosts_fake = {HOST_ID: HOST, 99: 99, 98: 98}

        self.expected_list_volumes = [
            BlockDeviceVolume(
                blockdevice_id=unicode(WWN1),
                size=int(WWN1_SIZE),
                attached_to=unicode(HOST),
                dataset_id=UUID(UUID1_STR)
            ),
            BlockDeviceVolume(
                blockdevice_id=unicode(WWN2),
                size=int(WWN2_SIZE),
                attached_to=unicode(HOST),
                dataset_id=UUID(UUID3_STR)
            ),
        ]
        mock_client = MagicMock

        mock_client.list_volumes = \
            MagicMock(return_value=self.list_volumes_fake)
        mock_client.get_vols_mapping = \
            MagicMock(return_value=self.get_vols_mapping_fake)
        mock_client.get_hosts = \
            MagicMock(return_value=self.get_hosts_fake)
        mock_client.backend_type = messages.SCBE_STRING

        mock_client.con_info.debug_level = DEFAULT_DEBUG_LEVEL
        mock_client.con_info.credential = dict(username='fake')

        self.driver_obj = driver.IBMStorageBlockDeviceAPI(
            UUID1_STR, mock_client, 'fakepool')

    def test_IBMStorageBlockDeviceAPI_list_volumes(
            self):
        self.assertEqual(
            self.driver_obj.list_volumes(),
            self.expected_list_volumes)

    def test_IBMStorageBlockDeviceAPI_list_volumes_with_one_not_attached(self):
        self.get_vols_mapping_fake.pop(WWN2)
        # update the attached_to=None
        self.expected_list_volumes[1] = BlockDeviceVolume(
            blockdevice_id=unicode(WWN2),
            size=int(WWN2_SIZE),
            attached_to=None,
            dataset_id=UUID(UUID3_STR)
        )

        self.assertEqual(
            self.driver_obj.list_volumes(),
            self.expected_list_volumes)

        self.get_vols_mapping_fake.pop(WWN1)
        # update the attached_to=None
        self.expected_list_volumes[0] = BlockDeviceVolume(
            blockdevice_id=unicode(WWN1),
            size=int(WWN1_SIZE),
            attached_to=None,
            dataset_id=UUID(UUID1_STR)
        )

        self.assertEqual(
            self.driver_obj.list_volumes(),
            self.expected_list_volumes)

    def test_IBMStorageBlockDeviceAPI_list_volumes_with_incomplete_attach(self):
        self.get_hosts_fake.pop(HOST_ID)
        # update the attached_to=None
        self.expected_list_volumes[0] = BlockDeviceVolume(
            blockdevice_id=unicode(WWN1),
            size=int(WWN1_SIZE),
            attached_to=None,
            dataset_id=UUID(UUID1_STR)
        )
        # update the attached_to=None
        self.expected_list_volumes[1] = BlockDeviceVolume(
            blockdevice_id=unicode(WWN2),
            size=int(WWN2_SIZE),
            attached_to=None,
            dataset_id=UUID(UUID3_STR)
        )

        self.assertEqual(
            self.driver_obj.list_volumes(),
            self.expected_list_volumes)


class TestBlockDeviceVerifyDefaultService(unittest.TestCase):
    """
    Unit testing for IBMStorageBlockDeviceAPI focus on default service.
    """

    def test_verify_default_service_exists__default_and_with_service_available(
            self):
        client = MagicMock
        client.list_service_names = MagicMock(return_value=['service1'])
        client.con_info.management_ip = None

        driver.verify_default_service_exists(
            driver.DEFAULT_SERVICE,
            client,
        )

    def test_verify_default_service_exists__default_and_no_service_exist(self):
        client = MagicMock
        client.list_service_names = MagicMock(return_value=[])
        client.con_info = Mock()
        self.assertRaises(
            driver.SCBENoServicesExist,
            driver.verify_default_service_exists,
            driver.DEFAULT_SERVICE,
            client,
        )

    def test_verify_default_service_exists__service_not_exist(self):
        client = MagicMock
        client.resource_exists = MagicMock(return_value=False)
        client.con_info = Mock()
        self.assertRaises(
            driver.StoragePoolNotExist,
            driver.verify_default_service_exists,
            'service1',
            client,
        )

    def test_verify_default_service_exists__service_exist(self):
        client = MagicMock
        client.resource_exists = MagicMock(return_value=True)
        client.con_info = Mock()

        driver.verify_default_service_exists(
            'service1',
            client,
        )

patch_factory = "ibm_storage_flocker_driver.ibm_storage_blockdevice." \
                "FactoryBackendAPIClient.factory"
patch_exists = "ibm_storage_flocker_driver.ibm_storage_blockdevice." \
               "verify_default_service_exists"


class TestBlockDeviceConfigurationFile(unittest.TestCase):
    """
    Unit testing for IBMStorageBlockDeviceAPI focus on reading yml file.
    """

    def test_get_connection_info_from_conf(self):
        conf_dict = {
            "management_ip": "x",
            "username": 'x',
            "password": "x",
        }

        connection_info = driver.get_connection_info_from_conf(conf_dict)
        expected = ConnectionInfo(
            conf_dict["management_ip"],
            conf_dict["username"],
            conf_dict["password"],
            port=None,
            verify_ssl=driver.DEFAULT_VERIFY_SSL,
            debug_level=driver.DEFAULT_DEBUG_LEVEL,
        )
        self.assertEqual(connection_info, expected)

    def test_get_connection_info_from_conf_with_port(self):
        conf_dict = {
            "management_ip": "x",
            "username": 'x',
            "password": "x",
            driver.CONF_PARAM_PORT: '999'
        }

        connection_info = driver.get_connection_info_from_conf(conf_dict)
        expected = ConnectionInfo(
            conf_dict["management_ip"],
            conf_dict["username"],
            conf_dict["password"],
            port=conf_dict[driver.CONF_PARAM_PORT],
            verify_ssl=driver.DEFAULT_VERIFY_SSL,
            debug_level=driver.DEFAULT_DEBUG_LEVEL,
        )
        self.assertEqual(connection_info, expected)

    def test_get_connection_info_from_conf_with_wrong_debug(self):
        conf_dict = {
            "management_ip": "x",
            "username": 'x',
            "password": "x",
            driver.CONF_PARAM_DEBUG: 'Wrong'
        }

        self.assertRaises(
            driver.YMLFileWrongValue,
            driver.get_connection_info_from_conf,
            conf_dict,
        )

    def test_get_connection_info_from_conf_with_wrong_ssl(self):
        conf_dict = {
            "management_ip": "x",
            "username": 'x',
            "password": "x",
            driver.CONF_PARAM_VERIFY_SSL: 'not a boolean'
        }

        self.assertRaises(
            driver.YMLFileWrongValue,
            driver.get_connection_info_from_conf,
            conf_dict,
        )

    @patch('ibm_storage_flocker_driver.ibm_storage_blockdevice.HostActions')
    @patch(patch_factory)
    @patch(patch_exists)
    def test_get_ibm_storage_backend_by_conf__verify_correct_log_level(
            self, hostaction, factory, exists):
        log_level = 'INFO'
        conf_dict = {
            "management_ip": "x",
            "username": 'x',
            "password": "x",
            "default_service": 'bronze',
            driver.CONF_PARAM_DEBUG: log_level,
        }
        driver.get_ibm_storage_backend_by_conf(UUID1_STR, conf_dict)
        self.assertEqual(driver.LOG.level, getattr(driver.logging, log_level))

        log_level = 'ERROR'
        conf_dict[driver.CONF_PARAM_DEBUG] = log_level
        driver.get_ibm_storage_backend_by_conf(UUID1_STR, conf_dict)
        self.assertEqual(driver.LOG.level, getattr(driver.logging, log_level))


GET_TOKEN_FUNC = 'ibm_storage_flocker_driver.lib.' \
                 'ibm_scbe_client.RestClient._get_token'


class TestBlockDeviceFactoryClient(unittest.TestCase):
    """
    Unit testing for FactoryBackendAPIClient
    """

    def test_factory_positive(self):
        factor_module = FactoryBackendAPIClient.get_module_dynamic('scbe')
        factor_class = FactoryBackendAPIClient.get_class_dynamic(
            factor_module, 'scbe')
        factor_class.__init__ = Mock(return_value=None)
        factor_class(Mock())

    def test_factory_negative(self):
        self.assertRaises(
            IBMDriverNoClientModuleFound,
            FactoryBackendAPIClient.get_module_dynamic,
            'fake_module_type',
        )

        factor_module = FactoryBackendAPIClient.get_module_dynamic('scbe')
        self.assertRaises(
            AttributeError,
            FactoryBackendAPIClient.get_class_dynamic,
            factor_module,
            'fake_module_type',
        )
