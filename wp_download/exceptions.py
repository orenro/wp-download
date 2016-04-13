# -*- coding: utf-8 -*-

# © Copyright 2009-2015 Wolodja Wentland. All Rights Reserved.

# This file is part of wp-download.
#
# wp-download is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# wp-download is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with wp-download. If not, see <http://www.gnu.org/licenses/>.
"""Error definition for wp_download.

This module defines errors raised within wp_download. All errors you might
encounter are subclasses of WPError, so that it is easy to catch all errors
wp_download.
"""

# -----------
# exit status

# wrong or missing argument
EARGUMENT = 2
# io error
EIO = 3
# error in template definition
ECTEMPLATE = 4
# general cfg file parsing error
ECPARSE = 5
# unexpected value in cfg file section
ECVALUE = 6
# no such file or directory
ENOENT = 7

# ----------
# exceptions

class WPError(Exception):
    """Base class for all errors in wp_download"""

    def __init__(self, *args):
        super(WPError, self).__init__(*args)


class WrappedError(WPError):
    """Base class for all error that wrap another exception"""

    def __init__(self, orig_err):
        super(WrappedError, self).__init__(*orig_err.args)
        self.orig_err = orig_err

# -------------
# configuration

class ConfigError(WrappedError):
    """Errors in the configuration file"""

    def __init__(self, config_file, **kw):
        super(ConfigError, self).__init__(**kw)
        self.config_file = config_file

    def __repr__(self):
        return '%s(file=%s)' % (self.__class__.__name__, self.config_file)

    def __unicode__(self):
        return u"Error in file '%s': %s" % (
            self.config_file, self.message)


class ConfigParseError(ConfigError):
    pass


class ConfigSectionError(ConfigError):
    """Errors specific to a given section in the configuration file"""

    def __init__(self, section, **kw):
        super(ConfigSectionError, self).__init__(**kw)
        self.section = section

    def __repr__(self):
        return '%s(file=%s, section=%s)' % (
            self.__class__.__name__, self.config_file, self.section)

    def __unicode__(self):
        return u"Error in section [%s] of '%s': %s" % (
            self.section, self.config_file, self.message)


class TemplateError(ConfigSectionError):
    """Base class for template errors"""

    def __init__(self, template, **kw):
        super(TemplateError, self).__init__(section='Templates', **kw)
        self.template = template

    def __repr__(self):
        return '%s(file=%s, template=%s)' % (
            self.__class__.__name__, self.config_file, self.template)


class TemplateMissingError(TemplateError):
    pass


class ConfigValueError(ConfigSectionError):
    pass

# --------
# download

class DownloadError(WPError):
    """This error is raised if a download has failed"""


class SkipDownload(WPError):
    """This exception is raised if a download should be skipped"""
