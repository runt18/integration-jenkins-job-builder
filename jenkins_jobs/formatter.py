#!/usr/bin/env python
# Copyright (C) 2015 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Manage interpolation of JJB variables into template strings.

import logging
from pprint import pformat
import re
from string import Formatter

from jenkins_jobs.errors import JenkinsJobsException

logger = logging.getLogger(__name__)


def deep_format(obj, paramdict, allow_empty=False):
    """Apply the paramdict via str.format() to all string objects found within
       the supplied obj. Lists and dicts are traversed recursively."""
    # YAML serialisation was originally used to achieve this, but that places
    # limitations on the values in paramdict - the post-format result must
    # still be valid YAML (so substituting-in a string containing quotes, for
    # example, is problematic).
    if hasattr(obj, 'format'):
        try:
            result = re.match('^{obj:(?P<key>\w+)}$', obj)
            if result is not None:
                ret = paramdict[result.group("key")]
            else:
                ret = CustomFormatter(allow_empty).format(obj, **paramdict)
        except KeyError as exc:
            missing_key = exc.message
            desc = "{0!s} parameter missing to format {1!s}\nGiven:\n{2!s}".format(
                missing_key, obj, pformat(paramdict))
            raise JenkinsJobsException(desc)
    elif isinstance(obj, list):
        ret = []
        for item in obj:
            ret.append(deep_format(item, paramdict, allow_empty))
    elif isinstance(obj, dict):
        ret = {}
        for item in obj:
            try:
                ret[CustomFormatter(allow_empty).format(item, **paramdict)] = \
                    deep_format(obj[item], paramdict, allow_empty)
            except KeyError as exc:
                missing_key = exc.message
                desc = "{0!s} parameter missing to format {1!s}\nGiven:\n{2!s}".format(
                    missing_key, obj, pformat(paramdict))
                raise JenkinsJobsException(desc)
    else:
        ret = obj
    return ret


class CustomFormatter(Formatter):
    """
    Custom formatter to allow non-existing key references when formatting a
    string
    """
    def __init__(self, allow_empty=False):
        super(CustomFormatter, self).__init__()
        self.allow_empty = allow_empty

    def get_value(self, key, args, kwargs):
        try:
            return Formatter.get_value(self, key, args, kwargs)
        except KeyError:
            if self.allow_empty:
                logger.debug(
                    'Found uninitialized key %s, replaced with empty string',
                    key
                )
                return ''
            raise
