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

import os.path

from nose.tools import raises, eq_

import wp_download.config as wpd_conf
import wp_download.error as wpd_err

PREFIX = os.path.join(*os.path.split(os.path.dirname(__file__))[:-1])
TEST_DATA_DIR = os.path.join(PREFIX, 'test', 'data')

def options_config(file):
    options = FakeOptions()
    options.config = os.path.join(TEST_DATA_DIR, file)
    return options

class FakeOptions(object):
    pass

class TestExampleConfiguration(object):

    def setup(self):
        options = FakeOptions()
        options.config = os.path.join(PREFIX, 'examples',
                                      'wpdownloadrc.sample')
        self.config = wpd_conf.Configuration(options)

    def test_enabled_languages(self):
        """config: wpdownloadrc.sample does not enable any languages"""
        assert len(list(self.config.enabled_languages())) == 0

    def test_filetypes(self):
        """config: wpdownloadrc.sample has proper filetype definitions"""

        for f in self.config.enabled_files():
            ft = self.config.get('Filetypes', f)
            assert ft in ['xml.bz2', 'sql.gz'], 'Filetype: %s' % (ft)

@raises(wpd_err.ConfigParseError)
def test_parse_error():
    """Configuration: Incomplete section headers -> ConfigParseError"""
    config = wpd_conf.Configuration(options_config('err_parse.cfg'))

def test_enabled_files():
    """Configuration.enabled_files: Check expected values"""
    config = wpd_conf.Configuration(options_config('enabled_options.cfg'))
    eq_(list(config.enabled_files()), ['langlinks', 'pages-articles',
                                       'redirect'])

@raises(wpd_err.ConfigParseError)
def test_ef_section_parse_error():
    """Configuration.enabled_files: Syntax errors -> ConfigParseError"""
    config = wpd_conf.Configuration(options_config('err_syntax.cfg'))
    files = list(config.enabled_files())

@raises(wpd_err.ConfigValueError)
def test_ef_section_value_error():
    """Configuration.enabled_files: Unexpected values -> ConfigValueError"""
    config = wpd_conf.Configuration(options_config('err_values.cfg'))
    files = list(config.enabled_files())

def test_enabled_languages():
    """Configuration.enabled_languages: Check expected values"""
    config = wpd_conf.Configuration(options_config('enabled_options.cfg'))
    eq_(list(config.enabled_languages()), ['tum', 'zh', 'zh_yue', 'zu'])

@raises(wpd_err.ConfigParseError)
def test_el_section_parse_error():
    """Configuration.enabled_languages: Syntax errors -> ConfigParseError"""
    config = wpd_conf.Configuration(options_config('err_syntax.cfg'))
    files = list(config.enabled_languages())

@raises(wpd_err.ConfigValueError)
def test_el_section_value_error():
    """Configuration.enabled_languages: Unexpected values -> ConfigValueError"""
    config = wpd_conf.Configuration(options_config('err_values.cfg'))
    files = list(config.enabled_languages())

@raises(wpd_err.TemplateMissingError)
def test_template_missing():
    """Configuration.string_template: Missing templates -> TemplateMissingError"""
    config = wpd_conf.Configuration(options_config('err_values.cfg'))
    template = config.string_template('no_such_template')
