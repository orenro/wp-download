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
"""Classes dealing with wp_download's configuration
"""

from __future__ import with_statement

import logging
import ConfigParser
import string

import wp_download.exceptions as wpd_exc

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class Configuration(ConfigParser.SafeConfigParser):
    """
    Configuration file data.
    """

    @property
    def config_file_path(self):
        """Get path of config file"""

        return self._options.config

    def __init__(self, options):
        """
        Constructor.
        """
        ConfigParser.SafeConfigParser.__init__(self)

        self._options = options
        self._parse_configuration()

    def _parse_configuration(self):
        """Parse the configuration file.
        """
        try:
            with open(self.config_file_path) as config_file:
                self.readfp(config_file)
        except ConfigParser.ParsingError as parse_err:
            raise wpd_exc.ConfigParseError(
                orig_err=parse_err, config_file=self.config_file_path)
        else:
            LOG.info('Read configuration from: %s' % (self.config_file_path))

    def enabled_options(self, section):
        """Generator of all enabled options in given section

        :param section: Name of the section
        :type section:  string
        """

        def _enabled_options(self):
            try:
                for opt in self.options(section):
                    if self.getboolean(section, opt):
                        yield opt
            except ValueError as val_err:
                raise wpd_exc.ConfigValueError(
                    orig_err=val_err, config_file=self.config_file_path,
                    section=section)
        return sorted(_enabled_options(self))

    def string_template(self, template_name):
        """Get a string template from the configuration file

        :param template_name:   Name of the template to return
        :type template_name:    string
        """
        LOG.debug('Read template: %s'%(template_name))

        try:
            return string.Template(
                self.get('Templates', template_name))
        except ConfigParser.NoOptionError as nop_err:
            raise wpd_exc.TemplateMissingError(
                orig_err=nop_err, config_file=self.config_file_path,
                template=template_name)

    def enabled_files(self):
        """Generator of all enabled files.
        """
        return self.enabled_options(section='Files')

    def enabled_languages(self):
        """Generator of all enabled languages.
        """
        return self.enabled_options(section='Languages')
