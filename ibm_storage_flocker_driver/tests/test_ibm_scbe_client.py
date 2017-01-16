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
from mock import patch, MagicMock
from bitmath import MiB
from ibm_storage_flocker_driver.lib.ibm_scbe_client import (
    IBMSCBEClientAPI,
    DEFAULT_SCBE_PORT,
    RestClient,
    RestClientException,
    HostIdNotFoundByWwn,
)
from ibm_storage_flocker_driver.lib import ibm_scbe_client
from ibm_storage_flocker_driver.lib.abstract_client import (
    VolInfo,
    ConnectionInfo,
)
from ibm_storage_flocker_driver.lib.constants import DEFAULT_DEBUG_LEVEL

FAKE_VOL_CONTENT = \
    '[' \
    '{"scsi_identifier":"6001738CFC9035E8000000000001348E",'\
    '"array_type":"2810XIV",'\
    '"array":"9835-415-6013800",' \
    '"array_name":"a9000",' \
    '"id":"6001738CFC9035E8000000000001348E",' \
    '"pool_name":"s1pool2",' \
    '"pool_id":"701a18900038",' \
    '"max_extendable_size":113364427776,' \
    '"service_compliance":"True",' \
    '"domain_name":"roei_domain",' \
    '"service_name":"s1",' \
    '"container_name":"Default_Space",' \
    '"service_id":"145d5b94-d573-45da-abac-6d625cc6970d",' \
    '"container_id":"5bba448a-6b9a-4d91-a369-758194a88c42",' \
    '"storage_model":"FlashSystem A9000R","' \
    'volume_id":"d55718f00053",' \
    '"name":"f_manual_vol",' \
    '"logical_capacity":10000000000,' \
    '"physical_capacity":10234101760,' \
    '"used_capacity":0,"last_update_time":"2016-10-13T10:45:52.588271",' \
    '"is_pending_deletion":false,' \
    '"serial":"",' \
    '"cg_id":"0",' \
    '"snapshot_time":null,' \
    '"compressed":true,' \
    '"ratio":0,' \
    '"saving":0,' \
    '"thin_provisioning_savings":"100",' \
    '"est_compression_factor":"1.00",' \
    '"pool":49,' \
    '"perf_class":null}]'

_RESTCLIENT_PATH = 'ibm_storage_flocker_driver.lib.ibm_scbe_client.RestClient'
GET_TOKEN_FUNC = _RESTCLIENT_PATH + '._get_token'

TOKEN_EXPIRED_STR = 'Token has expired'


class VolGetFakeRespond(object):

    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code


class TestsRESTClient(unittest.TestCase):
    """
    Unit testing for RestClient class
    """

    @patch(GET_TOKEN_FUNC)
    def test_client_init(self, get_token_mock):
        get_token_mock.return_value = 'FAKE TOKEN'
        con_info = ConnectionInfo(username='', password='',
                                  verify_ssl=False, management_ip='')
        r = RestClient(con_info, base_url='', auth_url='', referer='referer')
        self.assertEqual(r.session.headers['Authorization'],
                         'Token FAKE TOKEN')
        self.assertEqual(r.session.headers['Content-Type'], 'application/json')
        self.assertEqual(r.session.headers['referer'], 'referer')

    @patch('ibm_storage_flocker_driver.lib.ibm_scbe_client.requests')
    @patch(GET_TOKEN_FUNC)
    def test_client__generic_action(self, requests_mock, get_token_mock):
        get_token_mock.return_value = 'FAKE TOKEN'
        con_info = ConnectionInfo(username='', password='', verify_ssl=False,
                                  management_ip='')
        r = RestClient(con_info, base_url='', auth_url='', referer='referer')
        r._generic_action(action='get', resource_url='/url', payload=None)
        r.session.get.assert_called_once_with('/url', data='null')
        self.assertRaises(RestClientException,
                          r._generic_action,
                          action='get',
                          resource_url='/url',
                          payload=None,
                          exit_status=666)

    @patch('ibm_storage_flocker_driver.lib.ibm_scbe_client.requests')
    @patch(GET_TOKEN_FUNC)
    def test_client__get(self, requests_mock, get_token_mock):
        get_token_mock.return_value = 'FAKE TOKEN'
        r = RestClient(FAKE_MNG_INFO, base_url='', auth_url='',
                       referer='referer')
        r.session.get = MagicMock(
            return_value=VolGetFakeRespond(FAKE_VOL_CONTENT, 200))
        # Should pass without exception
        respond = r.get(resource_url='/url', payload=None)
        # trigger with right get params
        r.session.get.assert_called_once_with('/url', params=None)
        # check json.loads
        self.assertTrue(isinstance(respond, list))

    @patch('ibm_storage_flocker_driver.lib.ibm_scbe_client.requests')
    @patch(GET_TOKEN_FUNC)
    def test_client__get_bad_status_code(self, requests_mock, get_token_mock):
        get_token_mock.return_value = 'FAKE TOKEN'
        r = RestClient(FAKE_MNG_INFO, base_url='', auth_url='',
                       referer='referer')
        r.session.get = MagicMock(
            return_value=VolGetFakeRespond(FAKE_VOL_CONTENT, 201))
        self.assertRaises(RestClientException,
                          r.get,
                          resource_url='/url',
                          payload=None,
                          )
        try:
            # just double check, if it raises the right exception
            r.get(resource_url='/url', payload=None)
        except RestClientException as e:
            response = e.args[0]
            self.assertEqual(response.content, FAKE_VOL_CONTENT)
            self.assertEqual(response.status_code, 201)

class TestsRESTClientTokenExpire(unittest.TestCase):
    """
    Unit testing for RestClient class (Token Expiration)
    """

    @patch('ibm_storage_flocker_driver.lib.ibm_scbe_client.requests')
    @patch(GET_TOKEN_FUNC)
    def test_token_expire__get(self, requests_mock, get_token_mock):
        get_token_mock.return_value = 'FAKE TOKEN'
        r = RestClient(FAKE_MNG_INFO, base_url='', auth_url='',
                       referer='referer')
        r.session.get = MagicMock()
        r.session.get.side_effect = [
            VolGetFakeRespond(TOKEN_EXPIRED_STR,
                              RestClient.HTTP_EXIT_STATUS['UNAUTHORIZED']),
            VolGetFakeRespond(FAKE_VOL_CONTENT,
                              RestClient.HTTP_EXIT_STATUS['SUCCESS']),
        ]
        r.get(resource_url='/url', payload=None)

    @patch('ibm_storage_flocker_driver.lib.ibm_scbe_client.requests')
    @patch(GET_TOKEN_FUNC)
    def test_token_expire__get_second_also_fail(
            self, requests_mock, get_token_mock):
        get_token_mock.return_value = 'FAKE TOKEN'
        r = RestClient(FAKE_MNG_INFO, base_url='', auth_url='',
                       referer='referer')
        r.session.get = MagicMock()
        r.session.get.side_effect = [
            VolGetFakeRespond(TOKEN_EXPIRED_STR,
                              RestClient.HTTP_EXIT_STATUS['UNAUTHORIZED']),
            VolGetFakeRespond('fake, second time gets fail error', 666),
        ]
        self.assertRaises(
            RestClientException, r.get, resource_url='/url', payload=None
        )

    @patch('ibm_storage_flocker_driver.lib.ibm_scbe_client.requests')
    @patch(GET_TOKEN_FUNC)
    def test_token_expire__delete(self, requests_mock, get_token_mock):
        get_token_mock.return_value = 'FAKE TOKEN'
        r = RestClient(FAKE_MNG_INFO, base_url='', auth_url='',
                       referer='referer')
        r.session.delete = MagicMock()
        r.session.delete.side_effect = [
            VolGetFakeRespond(TOKEN_EXPIRED_STR,
                              RestClient.HTTP_EXIT_STATUS['UNAUTHORIZED']),
            VolGetFakeRespond(FAKE_VOL_CONTENT,
                              RestClient.HTTP_EXIT_STATUS['DELETED']),
        ]
        r.delete(resource_url='/url', payload=None)

    @patch('ibm_storage_flocker_driver.lib.ibm_scbe_client.requests')
    @patch(GET_TOKEN_FUNC)
    def test_token_expire__post(self, requests_mock, get_token_mock):
        get_token_mock.return_value = 'FAKE TOKEN'
        r = RestClient(FAKE_MNG_INFO, base_url='', auth_url='',
                       referer='referer')
        r.session.post = MagicMock()
        r.session.post.side_effect = [
            VolGetFakeRespond(TOKEN_EXPIRED_STR,
                              RestClient.HTTP_EXIT_STATUS['UNAUTHORIZED']),
            VolGetFakeRespond(FAKE_VOL_CONTENT,
                              RestClient.HTTP_EXIT_STATUS['CREATED']),
        ]
        r.post(resource_url='/url', payload=None)

FAKE_MNG_LOG_LEVEL = DEFAULT_DEBUG_LEVEL
FAKE_MNG_INFO = ConnectionInfo(
    username='', password='', verify_ssl=False,
    management_ip='', debug_level=FAKE_MNG_LOG_LEVEL
)

FAKE_SERVICE_NAME = 'service_name_1'
FAKE_SERVICES_OUT_PUT = [{
    "id": "145d5b94-d573-45da-abac-6d625cc6970d",
    "unique_identifier": "145d5b94-d573-45da-abac-6d625cc6970d",
    "name": FAKE_SERVICE_NAME,
    "description": " ",
    "container": "5bba448a-6b9a-4d91-a369-758194a88c42",
    "capability_values": "7",
    "type": "regular",
    "physical_size": 516822138880,
    "logical_size": 516822138880,
    "physical_free": 103364427776,
    "logical_free": 103364427776,
    "total_capacity": 516822138880,
    "used_capacity": 413457711104,
    "max_resource_logical_free": 103364427776,
    "max_resource_free_size_for_provisioning": 103364427776,
    "num_volumes": 2,
    "has_admin": True,
    "qos_max_iops": 0,
    "qos_max_mbps": 0
},
]

FAKE_VOL_WWN = 'YYYYY'
FAKE_VOL_ID = 1
FAKE_VOL_NAME = 'NAME'
FAKE_VOL_CAPACITY = int(MiB(100).to_Byte().value)
FAKE_VOLUME_LIST = [
    {
        "scsi_identifier": FAKE_VOL_WWN,
        "array_type": "2810XIV",
        "array": "9835-415-6013800",
        "array_name": "a9000",
        "id": "6001738CFC9035E80000000000013489",
        "pool_name": "s1pool1",
        "pool_id": "6c6118900031",
        "max_extendable_size": 17397972992,
        "service_compliance": "True",
        "domain_name": "roei_domain",
        "service_name": "s1",
        "container_name": "Default_Space",
        "service_id": "145d5b94-d573-45da-abac-6d625cc6970d",
        "container_id": "5bba448a-6b9a-4d91-a369-758194a88c42",
        "storage_model": "FlashSystem A9000R",
        "volume_id": FAKE_VOL_ID,
        "name": FAKE_VOL_NAME,
        "logical_capacity": FAKE_VOL_CAPACITY,
        "physical_capacity": 17397972992,
        "used_capacity": 0,
        "last_update_time": "2016-10-02T12:32:57.717462",
        "is_pending_deletion": False,
        "serial": "",
        "cg_id": "0",
        "snapshot_time": None,
        "compressed": True,
        "ratio": 0,
        "saving": 0,
        "thin_provisioning_savings": "100",
        "est_compression_factor": "1.00",
        "pool": 41,
        "perf_class": True
    },
]

FAKE_HOST = "docker-host"

FAKE_HOST_ID = 22
FAKE_MAPPING_JSON = [{
    "id": FAKE_HOST_ID,
    "volume": FAKE_VOL_WWN,
    "host": 45,
    "lun_number": 111,
}]
FAKE_HOST_JSON = {
    "id": FAKE_HOST_ID,
    "array_type": "XIV",
    "array": "fake",
    "host_id": "5ae18600013",
    "name": FAKE_HOST,
    "storage_cluster": None,
    "physical_host": 111,
}

WWN1 = '6001738CFC9035E80000000000014A81'
WWN2 = '6001738CFC9035E80000000000014A82'
HOST_ID = 45
HOST2_ID = 46


class TestsSCBEClient(unittest.TestCase):
    """
    Unit testing for IBMSCBEClientAPI class
    """

    @patch(_RESTCLIENT_PATH)
    def setUp(self, restclient_mock):
        self.client = IBMSCBEClientAPI(FAKE_MNG_INFO)

    def test_client_init(self):
        self.assertEqual(
            (self.client.con_info.port, self.client.con_info.verify_ssl),
            (DEFAULT_SCBE_PORT, False)
        )

    def test_list_service_names(self):
        self.client._client.get = MagicMock(return_value=FAKE_SERVICES_OUT_PUT)
        self.assertEqual(self.client.list_service_names(), [FAKE_SERVICE_NAME])

    def test_vol_list(self):
        self.client._client.get = MagicMock(return_value=FAKE_VOLUME_LIST)
        vol_info = VolInfo(FAKE_VOL_NAME, FAKE_VOL_CAPACITY, FAKE_VOL_ID,
                           FAKE_VOL_WWN)
        self.assertEqual(self.client.list_volumes(), [vol_info])

    def test_allocation_unit(self):
        self.assertEqual(self.client.allocation_unit(), 1024 * 1024)

    def test_vol_list2(self):
        fake_volinfo = VolInfo(FAKE_VOL_NAME, FAKE_VOL_CAPACITY, FAKE_VOL_ID,
                               FAKE_VOL_WWN)

        self.client.list_volumes = MagicMock(return_value=[fake_volinfo])
        self.client._vol_mapping_list = MagicMock(
            return_value=FAKE_MAPPING_JSON)
        self.client._host_by_id = MagicMock(return_value=FAKE_HOST_JSON)
        self.assertEqual(self.client.get_vol_mapping(FAKE_VOL_NAME), FAKE_HOST)

    def test__get_host_id_by_vol(self):
        fake_volinfo = VolInfo(FAKE_VOL_NAME, FAKE_VOL_CAPACITY, FAKE_VOL_ID,
                               FAKE_VOL_WWN)

        self.client.list_volumes = MagicMock(return_value=[fake_volinfo])
        self.client._host_list = MagicMock(return_value=None)
        self.assertRaises(
            HostIdNotFoundByWwn, self.client._get_host_id_by_vol,
            'WWN', 'HOST')

    def test_get_vols_mapping(self):
        get_vols_mapping_fake = [
            {"id": 1933, "volume": WWN2, "host": HOST_ID},
            {"id": 1934, "volume": WWN1, "host": HOST_ID},
        ]
        self.client._client.get = MagicMock(return_value=get_vols_mapping_fake)
        _expect = {WWN1: HOST_ID, WWN2: HOST_ID}
        self.assertEqual(_expect, self.client.get_vols_mapping())

        get_vols_mapping_fake[1]["host"] = HOST2_ID
        self.client._client.get = MagicMock(return_value=get_vols_mapping_fake)
        _expect = {WWN1: HOST2_ID, WWN2: HOST_ID}
        self.assertEqual(_expect, self.client.get_vols_mapping())

    def test_get_hosts(self):
        get_hosts_fake = [
            {
                "id": HOST_ID,
                "array_type": "2810XIV",
                "array": "9835-415-6013800",
                "host_id": "70811860002d",
                "name": FAKE_HOST,
                "storage_cluster": None,
                "physical_host": 28
            },
            {
                "id": HOST2_ID,
                "array_type": "2810XIV",
                "array": "9835-415-6013800",
                "host_id": "70811860002d",
                "name": FAKE_HOST + '1',
                "storage_cluster": None,
                "physical_host": 28
            }

        ]

        self.client._client.get = MagicMock(
            return_value=get_hosts_fake)
        _expect = {HOST_ID: FAKE_HOST, HOST2_ID: FAKE_HOST + '1'}
        self.assertEqual(_expect, self.client.get_hosts())

    def test_verify_log_level(self):
        _fake_mng_info = ConnectionInfo(
            username='', password='', verify_ssl=False,
            management_ip='', debug_level=FAKE_MNG_LOG_LEVEL
        )
        _fake_mng_info.debug_level = 'DEBUG'

        with patch(_RESTCLIENT_PATH):
            self.client = IBMSCBEClientAPI(_fake_mng_info)
        self.assertEqual(
            ibm_scbe_client.LOG.level,
            getattr(ibm_scbe_client.logging, _fake_mng_info.debug_level))

        _fake_mng_info.debug_level = 'ERROR'
        with patch(_RESTCLIENT_PATH):
            self.client = IBMSCBEClientAPI(_fake_mng_info)
        self.assertEqual(
            ibm_scbe_client.LOG.level,
            getattr(ibm_scbe_client.logging, _fake_mng_info.debug_level))
