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

import requests
import json
from bitmath import MiB
from functools import wraps
from ibm_storage_flocker_driver.lib import messages
from ibm_storage_flocker_driver.lib.abstract_client import (
    IBMStorageAbsClient, VolInfo, CreateVolumeError,
)
from ibm_storage_flocker_driver.ibm_storage_blockdevice import DEFAULT_SERVICE
import logging
from ibm_storage_flocker_driver.lib.utils import logme, config_logger

LOG = config_logger(logging.getLogger(__name__))

DEFAULT_SCBE_PORT = 8440
URL_SCBE_REFERER = 'https://{scbe_ip}:{scbe_port}/'
URL_SCBE_BASE_SUFFIX = 'api/v1'
URL_SCBE_RESOURCE_GET_AUTH = '/users/get-auth-token'
URL_SCBE_RESOURCE_VOLUME = '/volumes'
URL_SCBE_RESOURCE_SERVICE = '/services'
URL_SCBE_RESOURCE_MAPPING = '/mappings'
URL_SCBE_RESOURCE_HOST = '/hosts'
SCBE_FLOCKER_GROUP_PARAM = dict(group='flocker')
ALLOCATION_UNIT = int(MiB(1).to_Byte().value)
DEFAULT_SSL_PORT = 443


class RestClientException(Exception):
    """
    Use for every REST API response with unexpected exit status
    """


class RestClient(object):
    """
        Wrapper for http requests to provide easy REST API operations.
    """
    HTTP_EXIT_STATUS = dict(
        SUCCESS=200,
        CREATED=201,
        DELETED=204,
        UNAUTHORIZED=401,
    )
    LOG_PREFIX = 'rest_client :'
    AUTH_KEY = 'Authorization'

    def __init__(self, connection_info, base_url, auth_url, referer=None):
        """
        :param connection_info: ConnectionInfo
        :param base_url: where all the resource URL states
        :param auth_url: URL for initial authentication
        :param referer: URL referer
        """
        self.base_url = base_url
        self.auth_url = auth_url
        self.con_info = connection_info
        self.session = requests.Session()
        self.session.verify = connection_info.verify_ssl

        # Basic headers
        self.session.headers.update({'Content-Type': 'application/json'})
        if referer:
            self.session.headers.update({'referer': referer})

        self.get_token_and_update_header()

    def _retry_if_token_expire(func):
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except RestClientException as e:
                response = e.args[0]
                if response.status_code == \
                        self.HTTP_EXIT_STATUS['UNAUTHORIZED']:

                    LOG.debug(
                        messages.RAISED_UNAUTHORIZED_SO_RELOGIN_TO_GET_TOKEN.
                        format(func_name=func.__name__,
                               exception=e,
                               reason=getattr(response, 'reason', ''),
                               content=getattr(response, 'content', '')))

                    # Get new token
                    self.get_token_and_update_header()

                    # Run again the same REST API
                    return func(self, *args, **kwargs)
                else:
                    raise

        return wrapped

    def _generic_action(self, action, resource_url, payload=None,
                        exit_status=None):
        """
        Trigger request action on given URL and payload, and verify the
        respond exit_status.
        :param action:
        :param resource_url:
        :param payload:
        :param exit_status:
        :return: the request response
        """
        payload_json = json.dumps(payload)
        url = self.base_url + resource_url
        LOG.debug('http {} request to {} {}'.format(action, url, payload))
        response = getattr(self.session, action)(url, data=payload_json)
        self.verify_status_code(response, exit_status, action)
        return response

    def get_token_and_update_header(self):
        # remove the token from header if exist
        self.session.headers.pop(self.AUTH_KEY, None)

        token = self._get_token(self.auth_url, self.con_info.credential)

        # update token in header
        self.session.headers.update({self.AUTH_KEY: 'Token {}'.format(token)})

    def _get_token(self, resource_url, payload,
                   exit_status=HTTP_EXIT_STATUS['SUCCESS']):
        response = self._generic_action('post', resource_url, payload,
                                        exit_status)
        return response.json()['token']

    @_retry_if_token_expire
    def post(self, resource_url, payload=None,
             exit_status=HTTP_EXIT_STATUS['CREATED']):
        # TODO : Return json.loads
        return self._generic_action('post', resource_url, payload, exit_status)

    @_retry_if_token_expire
    def delete(self, resource_url, payload=None,
               exit_status=HTTP_EXIT_STATUS['DELETED']):
        return self._generic_action('delete', resource_url, payload,
                                    exit_status)

    @_retry_if_token_expire
    def get(self, resource_url, payload=None,
            exit_status=HTTP_EXIT_STATUS['SUCCESS']):
        """
        Send get request with params=payload
        :param resource_url:
        :param payload: parameters for the get request
        :param exit_status:
        :return: get response passed to json
        """
        url = self.base_url + resource_url
        LOG.debug('http get request to {} {}'.format(url, payload))
        response = self.session.get(url, params=payload)
        self.verify_status_code(response, exit_status, 'get')
        return json.loads(response.content)

    @staticmethod
    def verify_status_code(response, status_code, action):
        """
        Verify if response exit code is as expected.
        :param response:
        :param status_code:
        :param action:
        :raise RestClientException: When exit code is not as expected
        :return: None
        """
        if status_code is None:
            return None
        if response.status_code != status_code:
            reason = getattr(response, 'reason', '')
            content = getattr(response, 'content', '')
            raise RestClientException(
                response,
                "{} : Expect exist_code: {}, got: {}. "
                "reason : {}. content : {}".format(
                    action, status_code, response.status_code, reason, content)
            )


class ExceptionSCBEClient(Exception):
    pass


class VolumeNotFound(ExceptionSCBEClient):
    pass


class HostIDNotFound(ExceptionSCBEClient):
    def __init__(self, host_id, wwn):
        Exception.__init__(
            self,
            messages.HOST_NOT_FOUND_BY_VOLNAME.format(
                host_id, wwn),
        )


class HostIdNotFoundByWwn(ExceptionSCBEClient):
    def __init__(self, wwn, host, array, list_result):
        Exception.__init__(
            self,
            messages.HOST_NOT_FOUND_BY_WWN.format(
                wwn=wwn, host=host, array=array, list_result=list_result),
        )


class IBMSCBEClientAPI(IBMStorageAbsClient):
    backend_type = messages.SCBE_STRING

    def __init__(self, con_info):
        """
        IBM Spectrum Control Base Edition (SCBE) python client
        for IBM Flocker driver
        :param con_info: ConnectionInfo
        """
        super(IBMStorageAbsClient, self).__init__()
        self.con_info = self._set_defaults_for_con_info(con_info)
        LOG.setLevel(con_info.debug_level)

        referer = URL_SCBE_REFERER.format(
            scbe_ip=self.con_info.management_ip,
            scbe_port=self.con_info.port
        )
        base_url = referer + URL_SCBE_BASE_SUFFIX

        # Add the default SCBE Flocker group to the credentials
        self.con_info.credential.update(SCBE_FLOCKER_GROUP_PARAM)
        self._client = RestClient(
            self.con_info, base_url, URL_SCBE_RESOURCE_GET_AUTH, referer,
        )
        LOG.debug('Login to {} {}'.format(
            messages.SCBE_STRING, self.con_info.management_ip))

    @staticmethod
    def _set_defaults_for_con_info(con_info):
        if not con_info.port:
            con_info.port = DEFAULT_SCBE_PORT
        return con_info

    @logme(LOG)
    def create_volume(self, vol, resource, size):
        """
        :param vol:
        :param resource:
        :param size: in bytes
        :return: TODO, currently return the SCBE REST response
        """
        if not self.resource_exists(resource):
            msg = messages.VOLUME_CREATE_FAIL_BECAUSE_NO_SERVICES_EXIST.\
                format(vol, resource, self.con_info.management_ip)
            LOG.error(msg)
            raise CreateVolumeError(msg)

        # TODO should handle multiple services with same name
        payload = dict(
            service=self._service_list(name=resource)[0]['id'],
            name=vol,
            size=size,
            size_unit="byte",
        )
        return self._client.post(URL_SCBE_RESOURCE_VOLUME, payload)

    def _service_list(self, **kwargs):
        """
        :param kwargs: For filtering purposes, e.g name
        :return: list
        """
        return self._client.get(URL_SCBE_RESOURCE_SERVICE, kwargs)

    def _vol_list(self, **kwargs):
        return self._client.get(URL_SCBE_RESOURCE_VOLUME, kwargs)

    def list_volumes(self, wwn=None, vol_name=None, resource=None):
        """
        :param wwn:
        :param vol_name:
        :param resource: Not implemented for SCBE
        :return: list of VolInfo
        """
        payload = {}
        if wwn:
            payload["scsi_identifier"] = wwn
        if vol_name:
            payload["name"] = vol_name
        response = self._vol_list(**payload)
        return [self._get_vol_info(_vol) for _vol in response]

    @staticmethod
    def _get_vol_info(vol_rest_respond):
        """
        Convert volumes REST response to list of VolInfo objects
        :param vol_rest_respond:
        :return: list of VolInfo
        """
        return VolInfo(
            vol_rest_respond['name'],
            vol_rest_respond['logical_capacity'],
            vol_rest_respond['volume_id'],
            vol_rest_respond['scsi_identifier'],
        )

    @logme(LOG)
    def delete_volume(self, wwn):
        resource = '{}/{}'.format(URL_SCBE_RESOURCE_VOLUME, wwn)
        return self._client.delete(resource)

    @logme(LOG)
    def map_volume(self, wwn, host, lun=None):
        """
        map volume to host with given LUN
        (if lun not given find the next available LUNCkwif3h4a89hfitRwo-@2kwif3h4a89hf of the host)
        :param wwn: The WWN of the volume to map
        :param host: The host name in the storage system for mapping
        :param lun: LUN for mapping,
                    if not not found, the next available LUN
        :return:
        """
        host_id = self._get_host_id_by_vol(wwn, host)
        payload = dict(volume_id=wwn, host_id=host_id)
        if lun:
            payload['lun'] = lun
        return self._client.post(URL_SCBE_RESOURCE_MAPPING, payload)

    @logme(LOG)
    def _get_host_id_by_vol(self, wwn, host):
        """
        :param wwn: WWN of the volume
        :param host: The host name defined in the storage system
        :return: The host ID from the storage system of the volume
        """
        _vol = self._vol_list(scsi_identifier=wwn)
        if not _vol:
            raise VolumeNotFound(wwn)
        _vol = _vol[0]
        _host = self._host_list(array_id=_vol['array'], name=host)
        if not _host or len(_host) > 1:
            raise HostIdNotFoundByWwn(wwn, host, _vol['array'], _host)
        return _host[0]['id']

    def _host_list(self, **kwargs):
        """
        get host list by filters
        :return: list of dicts per matching host
        """
        return self._client.get(URL_SCBE_RESOURCE_HOST, kwargs)

    def _host_by_id(self, _id):
        """
        Get host object
        :param: id : The SCBE host ID
        :return: Dict with the host info that applies to the ID
        """
        url = '{}/{}'.format(URL_SCBE_RESOURCE_HOST, _id)
        return self._client.get(url)

    @logme(LOG)
    def unmap_volume(self, wwn, host):
        """
        Unmap a volume (by WWN) from given host
        :param wwn:
        :param host:
        :return:
        """
        host_id = self._get_host_id_by_vol(wwn, host)
        payload = dict(volume_id=wwn, host_id=host_id)
        return self._client.delete(URL_SCBE_RESOURCE_MAPPING, payload)

    def allocation_unit(self):
        return ALLOCATION_UNIT

    def resource_exists(self, resource):
        """
        Check if SCBE service exists for this SCBE Flocker interface
        :param resource: SCBE service name
        :return: boolean
        """
        return resource in (_service['name']
                            for _service in self._service_list(name=resource))

    def get_vol_mapping(self, wwn):
        """
        :param wwn: WWN of the volume
        :return: the host that mapped to this vol_name
                 (assume volume has only one mapping)
        :raise:
        """
        vol_mapping = self._vol_mapping_list(wwn)
        if not vol_mapping:
            return None
        host_id = vol_mapping[0]['host']
        host_name = self._host_by_id(host_id)
        if not host_name:
            raise HostIDNotFound(host_id, wwn)

        return host_name['name']

    def _vol_mapping_list(self, volume_wwn):
        """
        :param volume_wwn: vol id to show the mapping
        :return:
        """
        params = dict(volume=volume_wwn)
        return self._client.get(URL_SCBE_RESOURCE_MAPPING, params)

    def list_service_names(self):
        """
        :return: list of available services
        """
        return [_service['name'] for _service in self._service_list()]

    def handle_default_profile(self, default_profile):
        if default_profile is DEFAULT_SERVICE:
            raise Exception('TODO need to handle default profile later on')
        else:
            return default_profile

    def get_vols_mapping(self):
        """
        :return: dict of {[wwn]=[host_id],...}
        """
        mapping_list = self._client.get(URL_SCBE_RESOURCE_MAPPING)
        return {_map['volume']: _map['host'] for _map in mapping_list}

    def get_hosts(self):
        """
        :return: dict of {[host_id]=[hostname],...}
        """
        host_list = self._host_list()
        return {_host['id']: _host['name'] for _host in host_list}
