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

from flocker.node import BackendDescription, DeployerType
from ibm_storage_blockdevice import (
    get_ibm_storage_backend_by_conf,
    MANDATORY_CONFIGURATIONS_IN_YML_FILE,
)


def api_factory(cluster_id, **kwargs):
    return get_ibm_storage_backend_by_conf(cluster_id, kwargs)


FLOCKER_BACKEND = BackendDescription(
    name=u"ibm_storage_flocker_driver",
    needs_reactor=False,
    needs_cluster_id=True,
    required_config=MANDATORY_CONFIGURATIONS_IN_YML_FILE,
    api_factory=api_factory,
    deployer_type=DeployerType.block,
)
