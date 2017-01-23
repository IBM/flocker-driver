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

import os
import logging
import yaml
from twisted.trial.unittest import SkipTest
from ibm_storage_flocker_driver.ibm_storage_blockdevice import (
    get_ibm_storage_backend_by_conf,
)
from ibm_storage_flocker_driver.lib import messages
from ibm_storage_flocker_driver.lib.utils import config_logger

LOG = config_logger(logging.getLogger(__name__))


def get_ibm_storage_backend_from_environment(cluster_id):
    """
    :returns: An instance of IBMStorageBlockDeviceAPI
    """
    config_file_path = os.environ.get(messages.ENV_NAME_YML_FILE)
    if config_file_path is not None:
        config_file = open(config_file_path)
    else:
        raise SkipTest(messages.MISSING_ENV_FILE_FOR_TESTING)

    config = yaml.load(config_file.read())
    return get_ibm_storage_backend_by_conf(cluster_id, config['ibm'])


def detach_destroy_all_volumes(api):
    """
    Detach and destroy all volumes known to the API of this driver.
    :param : Driver API object
    """
    volumes = api.list_volumes()

    # pylint: disable=W0212
    msg = 'detach_destroy_all_volumes : ' \
          'cluster id [{}] has [{}] volumes : {}'.\
        format(
            api._cluster_id_slug,
            len(volumes),
            [(vol.blockdevice_id, vol.dataset_id) for vol in volumes],
        )
    LOG.debug(msg)

    for volume in volumes:
        if volume.attached_to is not None:
            api.detach_volume(volume.blockdevice_id)
        api.destroy_volume(volume.blockdevice_id)


def get_ibm_storage_blockdevice_api_for_test(cluster_id, test_case):
    """
    Create a ``IBMStorageBlockDeviceAPI`` instance for the tests
    (include the cleanup test).
    :param cluster_id: UUID, Flocker cluster ID
    :param test_case: Test case object
    :returns: A ``IBMStorageBlockDeviceAPI`` instance
    """
    api = get_ibm_storage_backend_from_environment(cluster_id)

    # pylint: disable=W0212
    LOG.setLevel(api._client.con_info.debug_level)
    test_case.addCleanup(detach_destroy_all_volumes, api)

    return api
