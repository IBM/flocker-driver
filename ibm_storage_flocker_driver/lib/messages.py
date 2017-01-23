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

SCBE_STRING = 'SCBE'
SCBE_FULL_NAME_STRING = 'IBM Spectrum Control Base Edition'
VERIFIED_AVAILABLE_SCBE_SERVICES = \
    SCBE_STRING + " services verified. (There are {} services available: {})"


VERIFIED_POOL_EXISTS = "Pool verified {}."
SERVICE_NAME_DOES_NOT_EXIST = \
    'No services exist in SCBE Flocker interface {}. ' \
    'Contact your storage administrator.'

VOLUME_CREATE_FAIL_BECAUSE_NO_SERVICES_EXIST = \
    'Cannot create volume [{}] on service [{}]. "\
    "Reason : Service does not exist or not delegated to the ' \
    'Flocker interface in [{}].' + SCBE_FULL_NAME_STRING

VOLUME_CREATE_FAIL_BECAUSE_NO_POOL_EXIST = \
    'Cannot create volume [{}] on pool [{}]. ' \
    'Reason : Pool does not exist on storage system [{}].'

WRONG_VALUE_FOR_YML_PARAMETER = \
    'Illegal value for parameter [{}], expected value is [{}].'

ENV_NAME_YML_FILE = 'IBM_STORAGE_CONFIG_FILE'
MISSING_ENV_FILE_FOR_TESTING = \
    'Missing mandatory environment named {} with the path to the ' \
    'test configuration file'.\
    format(ENV_NAME_YML_FILE)

CANNOT_DETACH_VOLUME_NOT_ATTACHED = \
    "Cannot detach a volume {} that is not attached to any host."

BLOCKDEVICE_NOT_ATTACHED_STOP_SEARCHING = \
    "blockdevice_id {} is not attached to any host. " \
    "(stop searching for device path)."

SUPPORT_ONLY_MULTIPATHING = 'Currently, only multipathing is supported.'
CANNOT_FIND_DEVICE_PATH = \
    "Cannot find device path for blockdevice_id {} volume name {}, " \
    "due to error {}"

POOL_NOT_EXIST_IN_ARRAY = \
    'Pool {pool} does not exist on storage system {array}.'

NO_DEVICE_FOUND_FOR_WWN = \
    'Device file for WWN {wwn} is not found. No clean-up is required.'

CMD_FAIL_TO_RUN = \
    "Command execution failure : {cmd}. " \
    "Error {exception}. " \
    "OUTPUT {output}. " \
    "retries {trynum} of {total_tries}"

PACKAGE_FORMAL_DESCRIPTION = \
    "IBM Storage Plugin for Flocker"

PACKAGE_FORMAL_KEYWORDS = [
    "backend", "plugin", "flocker", "docker",
    SCBE_FULL_NAME_STRING, "IBM",
]

BACKEND_TYPE_NOT_SUPPORTED = \
    'backend_type {backend_type} is not supported. ' \
    'Supported backend_type list is {supported_backends}'
NO_NEED_TO_CLEAN_IF_NO_MULTIPATHING = \
    'Multipath device clean-up is not required, ' \
    'as multipathing is disabled.'

MANDATORY_COMMAND_FOR_DRIVER_NOT_EXIST = \
    '{cmd} command is missing, {cmd} is mandatory for the driver.'

NO_ISCSIADM_CMD_EXIST = \
    "{cmd} command not found, " \
    "iSCSI will not be part of the rescaning process."

HOST_NOT_FOUND_BY_WWN = \
    "Host name [{host}] was not found on the storage system [{array}] that " \
    "related to " \
    "volume with WWN [{wwn}]. (Hosts that were found [{list_result}]."

HOST_NOT_FOUND_BY_VOLNAME = \
    "Host {host_id} was not found for volume {wwn}."

RAISED_UNAUTHORIZED_SO_RELOGIN_TO_GET_TOKEN = \
    'func [{func_name}] raised HTTP UNAUTHORIZED, ' \
    '(exception {exception}, {reason}, {content}).' \
    ' Regenerate token and rerun the same func.'

VOLUME_NOT_EXIST_IN_FLOCKER_CLUSTER = \
    'Volume [{volume}] does not exist in Flocker cluster ID [{cluster}].'

ISCSI_CMD_FAIL_BUT_CONTINUE_ON = \
    '{cmd} failed with error {exception}. Continue the OS rescanning anyway.'

MESSAGE_TYPE_ELIOT_LOG = "flocker:node:agents:blockdevice:ibm"

EXCEPTION_NO_MANAGEMENT_TYPE_EXIST = \
    "No Python module {module} exists for management type {mtype}."

DRIVER_INITIALIZATION = \
    PACKAGE_FORMAL_DESCRIPTION + ' is up and running.' \
    ' Plugin initialized with {backend_type} IP {backend_ip} ' \
    'and user name {username}.'

DRIVER_OPERATION_VOL_CREATE_WITH_PROFILE = \
    "Created a volume name {name}, size={size}, profile={profile}, WWN={wwn}"

DRIVER_OPERATION_VOL_DESTROY = \
    "Destroyed a volume name {volname}, WWN={wwn}"

DRIVER_OPERATION_VOL_CREATING = \
    "Creating a volume dataset_id={dataset_id}, size={size}, " \
    "on the default profile {default_profile}."

DRIVER_OPERATION_VOL_ATTACH = \
    "Attached volume WWN {blockdevice_id} to host {attach_to}."

DRIVER_OPERATION_VOL_DETTACH = \
    "Detached volume WWN {blockdevice_id} from host {attach_to}."

DRIVER_OPERATION_VOL_RESCAN_ISCSI = \
    'RESCAN: Executing OS iSCSI rescan: {cmd}'

DRIVER_OPERATION_VOL_RESCAN_OS = \
    'RESCAN: Executing OS rescan: {cmd}'

DRIVER_OPERATION_VOL_RESCAN_MULTIPATH = \
    'RESCAN: Executing multipathing rescan: {cmd}'

DRIVER_OPERATION_VOL_RESCAN_START_ATTACH = \
    'RESCAN: Executing rescan commands to discover device for ' \
    'WWN [{blockdevice_id}].'

DRIVER_OPERATION_VOL_RESCAN_START_DETACH = \
    'RESCAN: Executing rescan commands to clean device of ' \
    'WWN [{blockdevice_id}].'

DRIVER_OPERATION_GET_MULTIPATH_DEVICE = \
    'The device path of volume [{volname}] is [{device_path}] ' \
    '(checked by {cmd}).'

HOSTNAME_TO_BE_USE = \
    'Hostname [{hostname}] to be used in attach and detach driver' \
    ' operations on storage systems.'

INIT_CLIENT = 'Login to {backend} IP address {ip}.'

HTTP_REQUEST_DEBUG = 'HTTP {action} request to {url} {payload}'
