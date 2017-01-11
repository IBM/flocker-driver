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

import logging
from functools import wraps
from eliot import Message
from ibm_storage_flocker_driver.lib import messages

def logme(logger, prefix=None, level=logging.DEBUG):
    """
    Decorator for logging functions with args\kwargs and return value
    :param logger: Log to use
    :param prefix: Prefix if any
    :param level: Log level
    :return: func
    """
    def decorate(func):
        func_name = func.__name__
        func_module = func.__module__

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            _prefix = '(' + prefix + ') ' if prefix else ''
            logger.log(level, '{}.[{}]: {}Begin:{}{}'.format(
                func_module,
                func_name,
                _prefix,
                ' {}'.format('args {}'.format(args)) if args else '',
                ' {}'.format('kwargs {}'.format(kwargs)) if kwargs else ''))
            res = func(self, *args, **kwargs)
            return_str = ' {}'.format(
                'returned {}'.format(res) if res is not None else '')
            logger.log(level, '{}.[{}]:--> {}End:{}'.format(
                func_module,
                func_name,
                _prefix,
                return_str,
            ))
            return res
        return wrapper
    return decorate

class IBMStorageDriverLogHandler(logging.Handler):
    """ log handler for Eliot logging."""

    def emit(self, record):
        """
        Write log message to the Eliot stream.
        :param record:
        :return:
        """
        msg = self.format(record)
        Message.new(
            message_type=messages.MESSAGE_TYPE_ELIOT_LOG,
            message_level=record.levelname,
            message=msg).write()


def config_logger(log):
    """
    Set the write log level, add Eliot handler and prevent propagate multiple
    :param log:
    :return log:
    """
    log.setLevel(logging.DEBUG)
    log.addHandler(IBMStorageDriverLogHandler())
    log.propagate = False
    return log
