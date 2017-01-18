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

import socket
import logging
from uuid import UUID
from zope.interface import implementer
from twisted.python.filepath import FilePath

from flocker.node.agents.blockdevice import (
    AlreadyAttachedVolume,
    IBlockDeviceAPI,
    IProfiledBlockDeviceAPI,
    BlockDeviceVolume,
    UnknownVolume,
    UnattachedVolume,
)
from lib.host_actions import HostActions
from lib import host_actions
from ibm_storage_flocker_driver.lib import messages
from ibm_storage_flocker_driver.lib.abstract_client import (
    ConnectionInfo,
    FactoryBackendAPIClient,
)
from ibm_storage_flocker_driver.lib.utils import logme, config_logger
from ibm_storage_flocker_driver.lib.constants import (
    CONF_PARAM_BACKEND_TYPE,
    CONF_PARAM_DEBUG,
    DEFAULT_DEBUG_LEVEL,
    CONF_PARAM_DEBUG_OPTIONS,
    CONF_PARAM_VERIFY_SSL,
    DEFAULT_VERIFY_SSL,
    CONF_PARAM_PORT,
    DEFAULT_SERVICE,
    VOL_NAME_FLOCKER_PREFIX_LEN,
    END_INDEX_DATASET_ID_IN_VOL_NAME,
    START_CLUSTER_HASHED_INDEX,
    VOL_NAME_FLOCKER_PREFIX,
    VOL_NAME_DELIMITER_CLUSTER_HASHED,
)

LOG = config_logger(logging.getLogger(__name__))
PREFIX = 'API'  # log prefix


def get_ibm_storage_backend_by_conf(cluster_id, conf_dict):
    """
    Instantiate IBMStorageBlockDeviceAPI based on a given configuration dict.
    :param cluster_id: Flocker cluster id
    :param conf_dict: dict with all the backend configuration parameters
    :return: IBMStorageBlockDeviceAPI
    """
    # Get backend client object
    connection_info = get_connection_info_from_conf(conf_dict)
    backend_type = conf_dict.get(CONF_PARAM_BACKEND_TYPE, messages.SCBE_STRING)
    client = FactoryBackendAPIClient.factory(connection_info, backend_type)
    LOG.setLevel(connection_info.debug_level)

    # Verification
    default_resource = conf_dict[u"default_service"]
    verify_default_service_exists(default_resource, client)

    return IBMStorageBlockDeviceAPI(
        backend_client=client,
        cluster_id=cluster_id,
        storage_resource=default_resource,
    )


def get_connection_info_from_conf(conf_dict):
    """
    Build a ConnectionInfo object from the configuration dict.
    Define defaults if needed (e.g verify_ssl and debug).
    :param conf_dict:
    :return: ConnectionInfo
    """
    # Handle optional configurations
    debug = conf_dict.get(CONF_PARAM_DEBUG, DEFAULT_DEBUG_LEVEL)
    if debug not in CONF_PARAM_DEBUG_OPTIONS:
        raise YMLFileWrongValue(CONF_PARAM_DEBUG, CONF_PARAM_DEBUG_OPTIONS)

    verify_ssl = conf_dict.get(CONF_PARAM_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    if not isinstance(verify_ssl, bool):
        raise YMLFileWrongValue(CONF_PARAM_VERIFY_SSL, bool)

    port = conf_dict.get(CONF_PARAM_PORT)  # default set by the client object

    # Define Connection info from the configuration
    return ConnectionInfo(
        conf_dict[u"management_ip"],
        conf_dict[u"username"],
        conf_dict[u"password"],
        port=port,
        verify_ssl=verify_ssl,
        debug_level=debug,
    )


def verify_default_service_exists(default_service_name, client):
    """
    Check if default service exists or at least one service is available
    :param default_service_name:
    :param client: management client object
    :raises StoragePoolNotExist: if service does not exist
    :raises SCBENoServicesExist: if no services exist
    :return: None
    """
    if default_service_name == DEFAULT_SERVICE:
        scbe_services = client.list_service_names()
        if scbe_services:
            LOG.debug(messages.VERIFIED_AVAILABLE_SCBE_SERVICES.
                      format(len(scbe_services), scbe_services))
        else:
            raise SCBENoServicesExist(client.con_info.management_ip)
    elif client.resource_exists(default_service_name):
        LOG.debug(messages.VERIFIED_POOL_EXISTS.format(default_service_name))
    else:
        raise StoragePoolNotExist(default_service_name,
                                  client.con_info.management_ip)


def _get_blockdevicevolume(dataset_id, wwn, vol_size, attached_to=None):
    """
    :param dataset_id: UUID
    :param wwn: WWN of the volume
    :param vol_size:
    :param attached_to: The hostname attached to the volume
    :returns: ``BlockDeviceVolume```
    """

    return BlockDeviceVolume(
        blockdevice_id=unicode(wwn),
        size=vol_size,
        attached_to=attached_to,
        dataset_id=dataset_id,
    )


def uuid2slug(uuid_str):
    """
    :param uuid_str : str(UUID)
    :returns: ``encoded string of the given UUID```
    e.g : UUID('737d4ea0-28bf-11e6-b12e-68f7288f1809')->
          c31OoCi_EeaxLmj3KI8YCQ
    """

    encode = UUID(str(uuid_str)).bytes.encode('base64')
    # replace invalid char as vol name
    return encode.rstrip('=\n').replace('/', '_').replace('+', '-')


def slug2uuid(slug):
    """
    :param slug : string of encoded UUID
    :returns: str(UUID)
    """

    # replace back the orig slug
    orig_slug = (slug + '==').replace('_', '/').replace('-', '+')
    # decode
    return str(UUID(bytes=orig_slug.decode('base64')))


def get_dataset_id_from_vol_name(vol_name):
    """
    :param vol_name : The volume name
    :returns: UUID dataset_id: that is related to this volume name
    e.g :
        f_47eae400-28ce-11e6-b1ca-68f7288f1809_4124MijNEeaxymj3KI8YCQ
        f_<dataset-id 36 chars>_<cluster-id-slug 32 chars>
    """
    dataset_id_from_vol_name = vol_name[
        VOL_NAME_FLOCKER_PREFIX_LEN:END_INDEX_DATASET_ID_IN_VOL_NAME]
    return UUID(dataset_id_from_vol_name)


def get_cluster_id_slug_from_vol_name(vol_name):
    """
    :param vol_name : The volume name
    :returns: cluster_id that related to this volume name
    """
    return vol_name[START_CLUSTER_HASHED_INDEX:]


def build_vol_name(dataset_id, cluster_id_slug):
    """
    Build the volume name on template :
    f_<dataset-id 36 chars>_<cluster-id-slug 32 chars>
    :param dataset_id: UUID
    :param cluster_id_slug:
    :return: string
    """
    # TODO use storage metadata to store information like cluster_id of the vol
    return '{}{}{}{}'.format(
        VOL_NAME_FLOCKER_PREFIX,
        dataset_id,
        VOL_NAME_DELIMITER_CLUSTER_HASHED,
        cluster_id_slug,
    )


class StoragePoolNotExist(Exception):

    def __init__(self, pool, management_ip):
        Exception.__init__(
            self,
            messages.POOL_NOT_EXIST_IN_ARRAY.format(pool=pool,
                                                    array=management_ip))
        self.pool = pool


class SCBENoServicesExist(Exception):

    def __init__(self, management_ip):
        Exception.__init__(
            self,
            messages.SERVICE_NAME_DOES_NOT_EXIST.format(management_ip),
        )


class YMLFileWrongValue(Exception):

    def __init__(self, parameter_name, expected_value):
        Exception.__init__(
            self,
            messages.WRONG_VALUE_FOR_YML_PARAMETER.format(parameter_name,
                                                          expected_value),
        )


@implementer(IBlockDeviceAPI)
@implementer(IProfiledBlockDeviceAPI)
class IBMStorageBlockDeviceAPI(object):
    """
    A ``IBlockDeviceAPI`` and  ``IProfiledBlockDeviceAPI`` for IBM Storage.
    """

    @logme(LOG)
    def __init__(self, cluster_id, backend_client, storage_resource):
        """
        Initialize new instance of the IBM Storage Flocker driver.

        :param backend_client: IBMStorageAbsClient
        :param UUID cluster_id: The Flocker cluster ID
        :param storage_resource: The default resource for provisioning
        :raises MultipathCmdNotFound, RescanCmdNotFound:
                in case mandatory commands are missing
        """
        self._client = backend_client
        self._cluster_id = cluster_id
        self._storage_resource = storage_resource
        self._instance_id = self._get_host()
        self._cluster_id_slug = uuid2slug(self._cluster_id)
        self._host_ops = HostActions(backend_client.con_info.debug_level)
        self._is_multipathing = self._host_ops.is_multipath_active()
        LOG.info(messages.DRIVER_INITIALIZATION.format(
            backend_type=self._client.backend_type,
            backend_ip=self._client.con_info.management_ip,
            username=self._client.con_info.credential['username'],
        ))

    @staticmethod
    def _get_host():
        return unicode(socket.gethostname())

    def _get_volume(self, blockdevice_id):
        """
        Return BlockDeviceVolume if exists, else raise exception.

        :param unicode blockdevice_id: Name of the volume to check
        :raise: UnknownVolume - in case the volume does not exist
        :return: BlockDeviceVolume
        """
        return self._get_blockdevicevolume_by_vol(
            self._get_volume_object(blockdevice_id)
        )

    def _get_volume_object(self, blockdevice_id):
        """
        Return VolInfo if exist else raise exception.

        :param unicode blockdevice_id: Name of the volume to check
        :raise: UnknownVolume - in case volume not exist
        :return: BlockDeviceVolume
        """
        vol_objs = self._client.list_volumes(wwn=blockdevice_id)
        if not vol_objs:
            LOG.error("Volume does not exists: " + str(blockdevice_id))
            raise UnknownVolume(blockdevice_id)

        return vol_objs[0]

    def _volume_exist(self, blockdevice_id):
        """
        :param blockdevice_id:
        :return: Boolean
        """
        try:
            self._get_volume_object(blockdevice_id)
            return True
        except UnknownVolume:
            return False

    @logme(LOG, PREFIX)
    def compute_instance_id(self):
        """
        Get the backend-specific identifier for this node.

        This will be compared against ``BlockDeviceVolume.attached_to``
        to determine which volumes are locally attached and it will be used
        with ``attach_volume`` to locally attach volumes.

        :raise UnknownInstanceID: If we cannot determine the identifier
                                  of the node.
        :returns: A ``unicode`` object giving a provider-specific node
            identifier which identifies the node where the method is run.
        """
        return self._instance_id

    @logme(LOG, PREFIX)
    def allocation_unit(self):
        """
        The size in bytes up to which ``IDeployer`` will round volume
        sizes before calling ``IBlockDeviceAPI.create_volume``.

        :rtype: ``int``
        """
        return self._client.allocation_unit()

    @logme(LOG, PREFIX)
    def create_volume_with_profile(self, dataset_id, size, profile_name):
        """
        Create a new volume with the specified profile.

        When called by ``IDeployer``, the supplied size will be
        rounded up to the nearest ``IBlockDeviceAPI.allocation_unit()``.


        :param UUID dataset_id: The Flocker dataset ID of the dataset on this
            volume.
        :param int size: The size of the new volume in bytes.
        :param unicode profile_name: The name of the storage profile for this
            volume.

        :returns: A ``BlockDeviceVolume`` of the newly created volume.
        """
        volume_name = build_vol_name(dataset_id, self._cluster_id_slug)
        self._client.create_volume(
            vol=volume_name,
            resource=profile_name,
            size=size,
        )

        # TODO : improve performance by use the volume object during create
        vol_obj = self._client.list_volumes(resource=self._storage_resource,
                                            vol_name=volume_name)[0]

        LOG.info(messages.DRIVER_OPERATION_VOL_CREATE_WITH_PROFILE.format(
            name=vol_obj.name,
            size=vol_obj.size,
            profile=profile_name,
            wwn=vol_obj.wwn))

        return _get_blockdevicevolume(dataset_id, vol_obj.wwn, vol_obj.size)

    @logme(LOG, PREFIX)
    def create_volume(self, dataset_id, size):
        """
        Create a new volume.

        :param UUID dataset_id: The Flocker dataset ID of the dataset on this
            volume.
        :param int size: The size of the new volume in bytes.
        :returns: A ``BlockDeviceVolume``.
        """

        default_profile = self._client.handle_default_profile(
            self._storage_resource)

        LOG.info(messages.DRIVER_OPERATION_VOL_CREATING.format(
            dataset_id=dataset_id,
            size=size,
            default_profile=default_profile,
        ))

        return self.create_volume_with_profile(dataset_id, size,
                                               default_profile)

    @logme(LOG, PREFIX)
    def destroy_volume(self, blockdevice_id):
        """
        Destroy an existing volume.

        :param unicode blockdevice_id: The unique identifier for the volume to
            destroy.
        :raises UnknownVolume: If the supplied ``blockdevice_id`` does not
            exist.
        :return: ``None``
        """
        # raise exception if not exist
        vol = self._get_volume_object(blockdevice_id)
        self._client.delete_volume(blockdevice_id)
        LOG.info(messages.DRIVER_OPERATION_VOL_DESTROY.format(
            volname=vol.name,
            wwn=blockdevice_id,
        ))

    @logme(LOG, PREFIX)
    def attach_volume(self, blockdevice_id, attach_to):
        """
        Attach ``blockdevice_id`` to ``host``.

        :param unicode blockdevice_id: The unique identifier for the block
            device being attached.
        :param unicode attach_to: An identifier like the one returned by the
            ``compute_instance_id`` method indicating the node to which to
            attach the volume.
        :raises UnknownVolume: If the supplied ``blockdevice_id`` does not
            exist.
        :raises AlreadyAttachedVolume: If the supplied ``blockdevice_id`` is
            already attached.
        :returns: A ``BlockDeviceVolume`` with a ``host`` attribute set to
            ``host``.
        """
        # Raises UnknownVolume
        volume = self._get_volume(blockdevice_id)

        # raises AlreadyAttachedVolume
        if volume.attached_to is not None:
            LOG.error("Could Not attach Volume {} is already attached".
                      format(str(blockdevice_id)))
            raise AlreadyAttachedVolume(blockdevice_id)

        # Try to map the volume
        self._client.map_volume(wwn=blockdevice_id, host=attach_to)

        attached_volume = volume.set(attached_to=attach_to)
        LOG.info(messages.DRIVER_OPERATION_VOL_ATTACH.format(
            blockdevice_id=blockdevice_id, attach_to=attach_to))

        # Rescan the OS to discover the attached volume
        LOG.info(messages.DRIVER_OPERATION_VOL_RESCAN_START_ATTACH.format(
            blockdevice_id=blockdevice_id))
        self._host_ops.rescan_scsi()

        return attached_volume

    @logme(LOG, PREFIX)
    def detach_volume(self, blockdevice_id):
        """
        Detach ``blockdevice_id`` from whatever host it is attached to.

        :param unicode blockdevice_id: The unique identifier for the block
            device being detached.

        :raises UnknownVolume: If the supplied ``blockdevice_id`` does not
            exist.
        :raises UnattachedVolume: If the supplied ``blockdevice_id`` is
            not attached to anything.
        :returns: ``None``
        """
        # raises UnknownVolume
        volume = self._get_volume(blockdevice_id)

        # raises UnattachedVolume
        if volume.attached_to is None:
            LOG.error(messages.CANNOT_DETACH_VOLUME_NOT_ATTACHED.
                      format(str(blockdevice_id)))
            raise UnattachedVolume(blockdevice_id)

        self._clean_up_device_before_unmap(blockdevice_id)
        self._client.unmap_volume(wwn=blockdevice_id, host=volume.attached_to)
        LOG.info(messages.DRIVER_OPERATION_VOL_DETTACH.format(
            blockdevice_id=blockdevice_id, attach_to=volume.attached_to))

        # Rescan the OS to clean the detached volume
        LOG.info(messages.DRIVER_OPERATION_VOL_RESCAN_START_ATTACH.format(
            blockdevice_id=blockdevice_id))
        self._host_ops.rescan_scsi()

    @logme(LOG)
    def _clean_up_device_before_unmap(self, blockdevice_id):
        """
        The function cleans the multipath device.
        Use this function before unmapping a device from the backend.
        If a device is unmapped before cleaning the related multipath device,
        this may result in a faulty path. See example below.

        example of faulty devices :
        ----------------------------
        200173800fdf510eb dm-0 IBM     ,2810XIV
        size=16G features='1 queue_if_no_path' hwhandler='0' wp=rw
        `-+- policy='round-robin 0' prio=0 status=active
          |- 3:0:0:3 sdf 8:80  active faulty running
          `- 4:0:0:3 sdg 8:96  active faulty running

        :param blockdevice_id:
        :return: None
        """

        if not self._is_multipathing:
            LOG.debug(messages.NO_NEED_TO_CLEAN_IF_NO_MULTIPATHING)
            return
        try:
            device_path = self.get_device_path(blockdevice_id)
        except UnknownVolume:
            LOG.debug(messages.NO_DEVICE_FOUND_FOR_WWN.format(
                wwn=blockdevice_id))
            return

        self._host_ops.clean_mp_device(device_path.path)

    def _is_cluster_volume(self, vol_name):
        """
        Check if the volume is part of the Flocker cluster
        :param vol_name
        :return Boolean
        """
        if vol_name.startswith(VOL_NAME_FLOCKER_PREFIX):
            cluster_id_slug = get_cluster_id_slug_from_vol_name(vol_name)
            if cluster_id_slug == self._cluster_id_slug:
                return True
        return False

    @logme(LOG, PREFIX)
    def list_volumes(self):
        """
        List all the block devices available via the back end API.

        Only volumes for this particular Flocker cluster should be included.

        :returns: A ``list`` of ``BlockDeviceVolume``s.
        """
        volumes = []

        vol_list = self._client.list_volumes(resource=self._storage_resource)
        map_dict = self._client.get_vols_mapping()
        host_dict = self._client.get_hosts()

        for vol in vol_list:
            if not self._is_cluster_volume(vol.name):
                continue
            host_id = map_dict.get(vol.wwn)  # vol can be mapped to one host.
            hostname = host_dict.get(host_id) if host_id else None
            if hostname:
                hostname = unicode(hostname)
            attach_to = hostname
            vol_dataset_id = get_dataset_id_from_vol_name(vol.name)

            block_device_volume = _get_blockdevicevolume(
                vol_dataset_id,
                vol.wwn,
                vol.size,
                attach_to)
            volumes.append(block_device_volume)
        return volumes

    def _get_blockdevicevolume_by_vol(self, vol_obj):
        """
        return BlockDeviceVolume from VolInfo.

        :param vol_obj: VolInfo
        :raise UnknownVolume:
        :return: BlockDeviceVolume
        """
        if not self._is_cluster_volume(vol_obj.name):
            raise UnknownVolume(unicode(vol_obj.wwn))

        host = self._client.get_vol_mapping(vol_obj.wwn)
        host = unicode(host) if host else None

        vol_dataset_id = get_dataset_id_from_vol_name(vol_obj.name)
        block_device_volume = _get_blockdevicevolume(
            vol_dataset_id,
            vol_obj.wwn,
            vol_obj.size,
            host)
        return block_device_volume

    @logme(LOG, PREFIX)
    def get_device_path(self, blockdevice_id):
        """
        Return the device path that has been allocated to the block device on
        the host to which it is currently attached.

        :param unicode blockdevice_id: The unique identifier for the block
            device.
        :raises UnknownVolume: If the supplied ``blockdevice_id`` does not
            exist.
        :raises UnattachedVolume: If the supplied ``blockdevice_id`` is
            not attached to a host.
        :returns: A ``FilePath`` for the device.
        """
        # raises UnknownVolume
        vol_info = self._get_volume_object(blockdevice_id)
        volume = self._get_blockdevicevolume_by_vol(vol_info)

        if volume.attached_to is None:
            LOG.error(messages.BLOCKDEVICE_NOT_ATTACHED_STOP_SEARCHING.
                      format(str(blockdevice_id)))
            raise UnattachedVolume(blockdevice_id)

        if self._is_multipathing:
            # Assume OS rescan was already triggered
            # TODO consider to rescan if device was not found
            return self._get_device_multipath(vol_info.name, blockdevice_id)
        else:
            raise Exception(messages.SUPPORT_ONLY_MULTIPATHING)

    @logme(LOG)
    def _get_device_multipath(self, vol_name, blockdevice_id):
        """
        :param vol_name: Volume name for logging
        :param blockdevice_id: which is the WWN of the volume
        :return: A ``FilePath`` for the multipath device.
        """
        try:
            device_path = self._host_ops.get_multipath_device(
                vol_wwn=blockdevice_id)
        except (host_actions.MultipathDeviceNotFound,
                host_actions.MultipathDeviceFilePathNotFound,
                host_actions.CalledProcessError) as e:
            LOG.error(messages.CANNOT_FIND_DEVICE_PATH.format(
                str(blockdevice_id), vol_name, e))

            raise UnattachedVolume(blockdevice_id)
        device_path_obj = FilePath(device_path)
        LOG.info(messages.DRIVER_OPERATION_GET_MULTIPATH_DEVICE.format(
            volname=vol_name, device_path=device_path_obj.path,
            cmd=self._host_ops.multipath_cmd_ll))

        return device_path_obj
