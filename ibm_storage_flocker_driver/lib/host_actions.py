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

import re
import os
import logging
from distutils.spawn import find_executable
from subprocess import check_output, CalledProcessError, STDOUT
from ibm_storage_flocker_driver.lib import messages
from ibm_storage_flocker_driver.lib.utils import logme, config_logger
from ibm_storage_flocker_driver.lib.constants import DEFAULT_DEBUG_LEVEL

LOG = config_logger(logging.getLogger(__name__))

MULTIPATH_LINE_IDENTIFIER_RE = '{wwn}.* IBM'
PREFIX_DEVICE_PATH = '/dev/mapper'
TIMEOUT_FOR_MULTIPATH_CMD = 40

MULTIPATH_LIST_ARGS = " -v2 -ll"
RESCAN_CMDS = [
    'rescan-scsi-bus',
    'rescan-scsi-bus.sh',
]
ISCSIADM_CMD = 'iscsiadm'
MULTIPATH_CMD = 'multipath'
LOG_PREFIX = '{} : '.format(__name__)


class HostActions(object):

    def __init__(self, debug_level=DEFAULT_DEBUG_LEVEL):
        """
        Initialize host action object.
        TODO : Consider to use os-brick for rescan and get device.
        """
        LOG.setLevel(debug_level)

        # set required commands path
        self._rescan_cmd = self._find_rescan_cmd()

        self._iscsiadm_cmd = find_executable(ISCSIADM_CMD)
        if not self._iscsiadm_cmd:
            LOG.debug(messages.NO_ISCSIADM_CMD_EXIST.format(
                cmd=ISCSIADM_CMD))

        self._multipath_cmd = find_executable(MULTIPATH_CMD)
        if not self._multipath_cmd:
            raise MultipathCmdNotFound(MULTIPATH_CMD)

        self._multipath_cmd_ll = self._multipath_cmd + MULTIPATH_LIST_ARGS

    def check_out(self, cmd, cmd_list, msg, retries=0, wwn=None):
        """
        Execute check_output function and wrap it with retry flow

        :param cmd: Command to run
        :param cmd_list: Full command line
        :param msg: Message to log before
        :param retries: Number of retries if command fails
        :param wwn: If given, then stop retries if device is  found
        :return:
        """
        max_retries = retries
        LOG.debug(msg)
        while retries >= 0:
            try:
                out = check_output(cmd_list, stderr=STDOUT)
                LOG.debug(
                    'Finished CMD {} with output : \n{}'.format(cmd, out))
                break
            except CalledProcessError as e:
                msg = messages.CMD_FAIL_TO_RUN.format(
                    cmd=cmd, exception=str(e), output=e.output,
                    trynum=(max_retries - retries), total_tries=max_retries
                )
                LOG.error(msg)
                if retries == 0:
                    raise
                if wwn and self._get_multipath_device_native(wwn):
                    LOG.error("Stop retry because the wanted wwn (%s) "
                              "found in the %s" % (wwn, cmd))
                    break
                LOG.error("let try again to run the command %s" % cmd)
                retries -= 1

    @logme(LOG)
    def rescan_scsi(self, wwn=None, system_type=None):
        """
        Rescan SCSI bus - iscsi rescan, system rescan and multipath reload.
        This is needed for:
            - Resizing of volumes
            - Detaching of volumes
            - Possible creation of volumes
        :return:none
        """
        if self._iscsiadm_cmd:
            try:
                self.check_out(
                    self._iscsiadm_cmd,
                    [self._iscsiadm_cmd, "-m", "session", "--rescan"],
                    "iSCSI Rescanning the host")
            except CalledProcessError as e:
                '''
                    Continue to rescan even if the iscsiadm command fails.
                    For example, if no iSCSI target found, the command fails
                    but we still want to rescan the host.
                '''
                LOG.error(messages.ISCSI_CMD_FAIL_BUT_CONTINUE_ON.format(
                    cmd=self._iscsiadm_cmd,
                    exception=e,
                ))
                pass

        self.check_out(
            self._rescan_cmd,
            [self._rescan_cmd, "-r"],
            "Rescanning the host")

        self.check_out(
            self._multipath_cmd,
            ["timeout",
             TIMEOUT_FOR_MULTIPATH_CMD.__str__(),
             self._multipath_cmd,
             '-r'
             ],
            "Multipath rescan", retries=3, wwn=wwn)

        LOG.debug("Finish all rescans on the host")

    @classmethod
    def _find_rescan_cmd(cls):
        """
        Find the command path. If not, raise exception.
        :raise: RescanCmdNotFound
        :return: Command full path
        """
        for cmd in RESCAN_CMDS:
            found = find_executable(cmd)
            if found:
                return found
        raise RescanCmdNotFound(RESCAN_CMDS)

    @logme(LOG)
    def is_multipath_active(self):
        """"
        Verify if the native Linux multipath is active
        :return: Boolean
        """
        return True  # TODO currently assumes multipath is active

    @logme(LOG)
    def _get_multipath_device_native(self, vol_wwn):
        """
        Find the multipath device path /dev/mapper/[device] of a given WWN
        by using multipath -ll outout.

        Example :
        # example with XIV
        #> multipath -ll
        200173800fdf50f86 dm-0 IBM     ,2810XIV
        size=16G features='1 queue_if_no_path' hwhandler='0' wp=rw
        `-+- policy='round-robin 0' prio=1 status=active
          |- 3:0:0:1 sdb 8:16 active ready running
          `- 4:0:0:1 sdc 8:32 active ready running

        TODO Consider to handle also failing device like :
            200173800fdf51072 dm-0 ##,##
            size=16G features='1 queue_if_no_path' hwhandler='0' wp=rw
            `-+- policy='round-robin 0' prio=0 status=enabled
              `- #:#:#:# -   #:# failed faulty running

        # example with SVC
        #> multipath -ll
        36005076801d9053a180000000002ccd3 dm-0 IBM     ,2145
        size=1.0G features='1 queue_if_no_path' hwhandler='0' wp=rw
        `-+- policy='round-robin 0' prio=10 status=active
          |- 5:0:0:0 sdb 8:16 active ready running
          `- 7:0:0:0 sdc 8:32 active ready running

        # example redhat
        #> multipath -ll
        mpathd (36001738cfc9035e80000000000013aff) dm-8 IBM     ,2810XIV
        size=75G features='1 queue_if_no_path' hwhandler='0' wp=rw
        `-+- policy='service-time 0' prio=1 status=enabled
          |- 3:0:0:1 sdb 8:16 active ready running
          `- 5:0:0:1 sdc 8:32 active ready running

        :param vol_wwn:
        :return: str: the device path
        """
        cmd_out = check_output([self._multipath_cmd_ll], shell=True)
        LOG.debug("{multipath_cmd}   Out put : {output}".format(
            multipath_cmd=self._multipath_cmd_ll, output=cmd_out))

        for line in cmd_out.split('\n'):
            line_match = re.search(
                MULTIPATH_LINE_IDENTIFIER_RE.format(wwn=vol_wwn),
                line,
                flags=re.IGNORECASE
            )
            if line_match:
                device = line.split()[0]  # the first item is the device name
                return device

        LOG.error("device for vol_wwn {} not found in {}".format(
            vol_wwn, self._multipath_cmd_ll))
        return None

    @logme(LOG)
    def get_multipath_device(self, vol_wwn):
        """
        :param: vol_wwn:
        :raise: MultipathDeviceFilePathNotFound
        :return: DeviveAbsPath - Multipath device path
        """
        devmapper_device = self._get_multipath_device_native(vol_wwn)

        if not devmapper_device:
            raise MultipathDeviceNotFound(vol_wwn)

        device_fullpath = '{}/{}'.format(PREFIX_DEVICE_PATH, devmapper_device)

        if not os.path.exists(device_fullpath):
            LOG.error("device path {} not found".format(device_fullpath))
            raise MultipathDeviceFilePathNotFound(device_fullpath)

        LOG.debug(
            "device {} found in multipath -ll".format(device_fullpath))
        return device_fullpath

    @logme(LOG)
    def clean_mp_device(self, device_path):
        """
        Clean multipath device
        (use it before unmapping a volume from the storage system)

        :param device_path:
        :return:
        """
        mp_device_name = os.path.basename(device_path)

        self.run_cmd(
            ['dmsetup message {} 0 "fail_if_no_path"'.format(mp_device_name)])
        self.run_cmd(['multipath -f {}'.format(mp_device_name)], retries=3)

        LOG.debug("cleaned multiple device {}".format(device_path))

    @staticmethod
    def run_cmd(cmd, retries=0):
        max_retries = retries
        while retries >= 0:
            try:
                out = check_output(cmd, shell=True)
                LOG.debug("cmd {} output : {}".format(cmd, out))
                return out
            except Exception as e:
                LOG.error("%s: error, %s  (retries %s of %s)" % (
                    cmd, str(e), max_retries - retries, max_retries))
                if retries == 0:
                    raise
                LOG.error("let try again to run the command %s" % cmd)
                retries -= 1


class MultipathDeviceNotFound(Exception):
    pass


class MultipathDeviceFilePathNotFound(MultipathDeviceNotFound):
    pass


class RescanCmdNotFound(Exception):

    def __init__(self, cmds):
        Exception.__init__(
            self,
            messages.MANDATORY_COMMAND_FOR_DRIVER_NOT_EXIST.format(cmd=cmds),
        )
        self.cmds = cmds


class MultipathCmdNotFound(Exception):

    def __init__(self, cmd):
        Exception.__init__(
            self,
            messages.MANDATORY_COMMAND_FOR_DRIVER_NOT_EXIST.format(cmd=cmd),
        )
