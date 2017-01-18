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

# Constants related to volume name and dataset id
VOL_NAME_FLOCKER_PREFIX = 'f_'
VOL_NAME_DELIMITER_CLUSTER_HASHED = '_'
NUM_CHARS_IN_UUID = 36
START_CLUSTER_HASHED_INDEX = (
    len(VOL_NAME_FLOCKER_PREFIX) +
    NUM_CHARS_IN_UUID +
    len(VOL_NAME_DELIMITER_CLUSTER_HASHED)
)
DATASET_ID_NUM_CHARS = NUM_CHARS_IN_UUID  # based on UUID
VOL_NAME_FLOCKER_PREFIX_LEN = len(VOL_NAME_FLOCKER_PREFIX)
END_INDEX_DATASET_ID_IN_VOL_NAME = (
    DATASET_ID_NUM_CHARS + VOL_NAME_FLOCKER_PREFIX_LEN
)

# Constants related to YML file parameters and defaults
DEFAULT_DEBUG_LEVEL = 'INFO'  # aka default log_level
DEFAULT_SERVICE = '-DEFAULT-'
DEFAULT_VERIFY_SSL = True
MANDATORY_CONFIGURATIONS_IN_YML_FILE = {
    u"username",
    u"password",
    u"management_ip",
    u"default_service"
}
CONF_PARAM_PORT = u"management_port"
CONF_PARAM_DEBUG = u"log_level"
CONF_PARAM_BACKEND_TYPE = u"management_type"
CONF_PARAM_VERIFY_SSL = u"verify_ssl_certificate"
OPTIONAL_CONFIGURATIONS_IN_YML_FILE = {
    CONF_PARAM_BACKEND_TYPE,
    CONF_PARAM_DEBUG,
    CONF_PARAM_VERIFY_SSL,
    CONF_PARAM_PORT,
}
CONF_PARAM_DEBUG_OPTIONS = ["DEBUG", "INFO", "WARN", "ERROR"]
