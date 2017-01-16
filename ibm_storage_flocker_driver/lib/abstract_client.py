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

import abc
import pkgutil
import messages

class ExceptionStorageClient(Exception):
    pass


class CreateVolumeError(ExceptionStorageClient):
    pass


class ConnectionInfo(object):

    def __init__(self, management_ip, username, password, port=None,
                 verify_ssl=None, debug_level=None):
        """
        This object holds connection information about the management system.
        :param management_ip:
        :param username:
        :param password:
        :param port:
        :param verify_ssl:
        """
        self.management_ip = management_ip
        self.port = port
        self.verify_ssl = verify_ssl
        self.debug_level = debug_level
        # TODO consider to support specific SSL certification path
        self.credential = dict(
            username=username,
            password=password,
        )

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class VolInfo(object):

    def __init__(self, name, size_bytes, vol_id, wwn):
        """
        Holds the minimal information that Flocker driver needs to know about
        a volume
        :param name: Volume name
        :param size_bytes: Volume size
        :param vol_id: Volume ID
        :param wwn: Volume iSCSI identifier
        """
        self.name = name
        self.size = size_bytes
        self.id = vol_id
        self.wwn = wwn

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class IBMStorageAbsClient(object):
    # TODO consider to use from zope.interface.Interface instead of abc
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, con_info):
        """
        :param con_info: ConnectionInfo
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create_volume(self, vol, resource, size):
        """
        :param vol:
        :param resource: A service name or a pool name
        :param size: In bytes
        :return: SCBE REST response (TODO : VolInfo)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list_volumes(self, wwn=None, vol_name=None, resource=None):
        """
        :param wwn:
        :param vol_name:
        :param resource: Relevant only for direct mode
        :return: list of VolInfo
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_volume(self, wwn):
        """
        :param wwn:
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def map_volume(self, wwn, host, lun=None):
        """
        map a volume to a host
        :param wwn: The WWN of the volume to map
        :param host: The host name in the storage system for mapping
        :param lun: LUN for mapping, if None the function will
                    find automatically the next available LUN.
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def unmap_volume(self, wwn, host):
        """
        unmap a volume from the host
        :param wwn:
        :param host:
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def allocation_unit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def resource_exists(self, resource):
        """
        Check if storage resource exists (service or pool)
        :param resource:
        :return: boolean
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_vol_mapping(self, wwn):
        """
        :param wwn: WWW of the volume
        :return: The host mapped to this vol_name
                 (assuming that the volume has only one mapping)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list_service_names(self):
        """
        :return: list of available services
        """
        raise NotImplementedError

    @abc.abstractmethod
    def handle_default_profile(self, default_profile):
        """
        Identify the default profile
        :param: default_profile
        :return: The right default profile based on logic
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_vols_mapping(self):
        """
        :return: dict of {[wwn]=[host_id],...}
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_hosts(self):
        """
        :return: dict of {[host_id]=[hostname],...}
        """
        raise NotImplementedError


class FactoryBackendAPIClient(object):
    """
    Create the backend API client by given management type.
    It's plugable to new management type like direct mode to storage systems.
    Currently, we support only SCBE (IBM Spectrum Control Base Edition) as the
    management system.

    Instructions on how to add a new management plug-in:
    Add a module with file convention lib.ibm_<NEW>_client.py,
    This new module should implement lib.abstract_client.IBMStorageAbsClient.
    The name of the class should be IBMStorage<NEW>Client.
    """
    @staticmethod
    def get_module_dynamic(backend_type):
        """
        :param backend_type: String
        :return: module lib.ibm_<backend_type>_client by given backend_type
        :raise: IBMDriverNoClientModuleFound if module not found
        """
        module_name = 'ibm_storage_flocker_driver.lib.ibm_{}_client'.format(
            str(backend_type).lower())
        pkgutil_import_module = pkgutil.find_loader(module_name)
        if not pkgutil_import_module:
            raise IBMDriverNoClientModuleFound(module_name, backend_type)

        import_module_object = pkgutil_import_module.load_module(
            module_name)
        return import_module_object

    @staticmethod
    def get_class_dynamic(module_object, backend_type):
        """
        :param module_object: module lib.ibm_<backend_type>_client
        :param backend_type: string
        :return: IBM<backend_type>ClientAPI class from the given module
        :raise: AttributeError if class does not exist in given module
        """
        class_name = 'IBM{}ClientAPI'.format(str(backend_type).upper())
        class_object = getattr(module_object, class_name)
        return class_object

    @classmethod
    def factory(cls, connection_info, backend_type):
        """
        Create backend client object
        :param connection_info: ConnectionInfo
        :param backend_type: String
        :return: IBM<backend_type>ClientAPI object
        """
        class_object = cls.get_class_dynamic(
            cls.get_module_dynamic(backend_type), backend_type)
        return class_object(connection_info)


class IBMDriverNoClientModuleFound(Exception):

    def __init__(self, module_path, mtype):
        Exception.__init__(
            self,
            messages.EXCEPTION_NO_MANAGEMENT_TYPE_EXIST.format(
                module=module_path,
                mtype=mtype),
        )
