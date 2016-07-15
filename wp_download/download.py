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
"""Classes for retrieving Wikipedia dumps.
"""

from __future__ import with_statement

import logging
import urllib
import os
import urlparse
import re
import datetime
import progressbar
import socket

from contextlib import nested, closing

import wp_download.exceptions as wpd_exc
import wp_download.config as wpd_conf

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def init_progressbar(path, maxval):
    """Initialise progressbar

    :param maxval:  The maximum expected value
    :type maximum:  int
    """

    widgets = [os.path.basename(path), ' ',
               progressbar.Bar(left='[', right=']', marker='*'), ' ',
               progressbar.Percentage(), ' ', progressbar.ETA(), ' ',
               progressbar.FileTransferSpeed()]

    return progressbar.ProgressBar(widgets=widgets, maxval=maxval)


class ErrorLimit(logging.Filter):
    """Discard all records with a level higher or equal to
    logging.ERROR
    """

    def filter(self, record):
        """Filter log record by level

        :param record:  Log record in question
        :type record:   logging.LogRecord
        """

        if record.levelno < logging.ERROR:
            return True
        return False


class PartialDownloader(urllib.FancyURLopener):
    """Subclass that overrides error 206.

    This error means a partial file is being sent, which is ok in this case.
    Do nothing with this error.
    """

    def http_error_206(self, *args, **kw):
        """This error is raised for partial downloads"""


class WPDownloader(object):
    """
    Downloader for Wikipedia database dumps.
    """

    def __init__(self, options):
        """
        Constructor.
        """
        self._options = options
        self._config = wpd_conf.Configuration(options)
        self._urlhandler = URLHandler(self._config, options)
        self._downloader = urllib.FancyURLopener()

        LOG.info('Set timeout to %d' % (options.timeout))

        socket.setdefaulttimeout(options.timeout)

    def _download_directory(self, language, path):
        """Get download directory for given language at path

        :param language:    ISO 631 language code
        :type language:     string

        :param path:    Base path for language directories
        :type path:     string
        """
        return os.path.join(path, language,
                self._urlhandler.latest_dump_date(
                    language).strftime('%Y%m%d'))

    def _create_download_dirs(self, language, path):
        """Create directories for given language

        :param path:    Path where directories should be created
        :type path:     string
        """
        down_dir = self._download_directory(language, path)

        if not os.path.exists(down_dir):
            LOG.info('Creating directory: %s' % (down_dir))
            os.makedirs(down_dir)

    def _remote_content_length(self, url):
        """Get content length of file at given URL.

        :param url:     URL
        :type url:      string

        :returns:       Content length of file at URL
        :rtype:         int
        """
        with closing(self._downloader.open(url)) as remote_file:
            if remote_file.getcode() >= 300:
                return 0
            return int(remote_file.headers['Content-Length'])

    def _should_skip_url(self, url, path):
        """Should we skip retrieval of the file at given URL?

        URLs are skipped if a local file with the same size as the remote one
        exists and retrieval of all files was not forced by the user.

        :param url:     URL of the remote file
        :type url:      string

        :param path:    Path where remote file would be saved
        :type path:     string

        :returns:       True if retrieval should be skipped, False otherwise
        :rtype:         boolean
        """
        if os.path.exists(path):
            if (self._remote_content_length(url) == os.path.getsize(path)
                and not self._options.force):
                return True
        return False

    def _offset(self, url, path):
        """Get download offset for file at given URL.

        :param url:     URL of the remote file
        :type url:      string

        :param path:    Path where remote file would be saved
        :type path:     string

        returns:        Download offset (ie size(remote) - size(local))
        :rtype:         int
        """
        if self._options.resume and os.path.exists(path):
            local_file_size = os.path.getsize(path)
            if self._remote_content_length(url) >= local_file_size:
                return local_file_size
        return 0

    def retrieve_files(self, urls, path):
        """Save all files to given path

        :param urls:    Iterable of URLs that should be downloaded
        :type urls:     list/iterator/...

        :param path:    Path where directories should be created
        :type path:     string
        """

        for url in urls:
            file_path = os.path.join(path, os.path.basename(url))

            if self._should_skip_url(url, file_path):
                LOG.info('Skipped: %s' % (os.path.basename(url)))
                continue

            try:
                self.retrieve_file(url, file_path)
            except wpd_exc.DownloadError:
                LOG.error('DownloadError: %s' % (os.path.basename(url)))
                continue

    def retrieve_file(self, url, path):
        """Retrieve a single file

        :param url:     Download URL of file
        :type url:      string

        :param path:    Local path where file should be saved
        :type path:     string
        """
        tries = 0
        # Add a trailing .part suffix so that partial files are
        # flagged as such
        path = path + ".part"

        while True:
            if tries == self._options.retries:
                raise wpd_exc.DownloadError('Could not retrieve file: %s' % (
                    os.path.basename(url)), 'Retry limit exceeded')
            try:
                self.retrieve(url, path)
                # Remove the trailing .part suffix
                os.rename(path, os.path.splitext(path)[0])
                break
            except socket.error as s_err:
                LOG.error('Socket Error: %s' % (s_err))
            except IOError as io_err:
                LOG.error(io_err)
            except wpd_exc.DownloadError as down_err:
                LOG.error(down_err)
            finally:
                tries += 1

    def retrieve(self, url, path):
        """Copy content from URL to file at path.

        :param url:     Download URL of file
        :type url:      string

        :param path:    Local path where file should be saved
        :type path:     string
        """
        block_size = 8 * 1024
        read = 0
        offset = self._offset(url, path)
        downloader = PartialDownloader()
        downloader.addheader('Range', 'bytes=%s-' % (offset))

        with closing(downloader.open(url)) as remote_file:
            if remote_file.getcode() >= 300:
                raise wpd_exc.DownloadError(
                    'Got HTTP response code: %d for file %s' %
                    (remote_file.getcode(), os.path.basename(path)))

            with open(path, 'ab') as local_file:
                if offset:
                    LOG.info('Resume: %s' % (os.path.basename(path)))
                    local_file.seek(offset)

                content_length = self._remote_content_length(url)

                try:
                    if not self._options.quiet:
                        pbar = init_progressbar(path, content_length)
                        pbar.start()
                        if offset:
                            pbar.update(offset)
                            read = offset

                    for block in iter(lambda: remote_file.read(block_size), ''):
                        local_file.write(block)
                        read += len(block)

                        if read > content_length:
                            raise wpd_exc.DownloadError(
                                'Received data exceeds advertised size: %s' % (
                                    os.path.basename(path)))

                        if not self._options.quiet:
                            pbar.update(read)
                finally:
                    if not self._options.quiet:
                        pbar.finish()

    def download_language(self, language, path):
        """Download all files for given language

        :param language:    ISO 631 language code
        :type language:     string

        :param path:        Base path where the language directory will be
                            created.
        :type path:         string
        """
        self._create_download_dirs(language, path)

        self.retrieve_files(
            self._urlhandler.urls_for_language(language),
            self._download_directory(language, path))

    def download_all_languages(self, path):
        """Download files for all enabled languages

        :param path:        Base path where the language directories will be
                            created.
        :type path:         string
        """

        for lang in self._config.enabled_languages():
            LOG.info('Processing language: %s' % lang)

            try:
                self.download_language(lang, path)
            except IOError:
                LOG.error('Download failed: %s' % (lang))
                LOG.error('Skipped: %s' % (lang))
                continue


class URLHandler(object):
    """
    Handler for Wikipedia dump download URLs
    """

    def __init__(self, config, options=None):
        """
        Constructor.

        :param config:	Configuration
        """
        assert config
        self._config = config

        self._urlopener = urllib.FancyURLopener()
        self._date_matcher = re.compile(r'<a href="(\d{8})/">.*/</a>')

        self._host = self._config.get('Configuration', 'base_url')

        self._lang_dir_template = self._config.string_template(
            'language_dir_format')
        self._filename_template = self._config.string_template('file_format')
        self._custom_dump = []
        if options and options.custom_dump:
            self._custom_dump.extend(options.custom_dump)

    def language_dir(self, language):
        """Get the directory for given language

        :param language:    ISO 631 language code
        :type language:     string
        """
        if language == 'entities':
            return 'wikidatawiki/entities'
        else:
            return self._lang_dir_template.substitute(langcode=language)

    def language_url(self, language):
        """Get the dump location for given language

        :param language:    ISO 631 language code
        :type language:     string
        """
        return urllib.basejoin(self._host, self.language_dir(language))

    def dump_dates(self, url):
        """Iterator containing datetime objects that correspond to the creation
        dates of the dumps found at given url.

        :param url: URL pointing to a mediawiki language download page
        :type url:  string

        :raises ValueError: A ValueError is raised if no date could be
                            extracted from given URL.
        """
        try:
            with closing(self._urlopener.open(url)) as lang_site:
                return (datetime.datetime.strptime(date, '%Y%m%d') for date in
                         self._date_matcher.findall(lang_site.read()))
        except IOError as io_err:
            LOG.error(io_err)
            LOG.error('Could not retrieve: %s' % (url))
            raise io_err

    def latest_dump_date(self, language):
        """Get the lates dump date for given language.

        :raises ValueError: A ValueError is raised if no date could be
                            extracted from given URL.

        :returns:   The latest dump date
        :rtype:     datetime.datetime
        """
        custom_dates = dict(
            [pair.split(':', 1) for pair in self._custom_dump])
        if language in custom_dates:
            return datetime.datetime.strptime(custom_dates[language], '%Y%m%d')

        dates = [ d for d in self.dump_dates(self.language_url(language)) ] + \
            [ datetime.datetime.strptime('19000101', '%Y%m%d') ]
        return max(dates)

    def urls_for_language(self, language):
        """Iterator for all file URLs to download.

        The iterator will yield elements of the form (lang, url).

        This function will parse the provided wp-download configuration files,
        query the WikiMedia download website

        :param language:    ISO 631 language code
        :type language:     string

        :raises ValueError: A ValueError is raised if URL construction failed.
        """
        try:
            latest = self.latest_dump_date(language)
        except IOError as io_err:
            LOG.error('Could not get dump date for %s!' % (language))
            LOG.error('Skip: %s'%(language))
            LOG.error(io_err)
            yield

        LOG.info('Latest dump for (%s) is from %s' % (
            language, latest.strftime('%A %d %B %Y')))

        filetypes = self._config.enabled_files()
        for filename in filetypes:
            if language == 'entities':
                server_path = '/'.join([
                    self.language_dir(language),
                    latest.strftime('%Y%m%d'),
                    'wikidata-%s-all.json.gz' % latest.strftime('%Y%m%d')])
            else:
                server_path = '/'.join([
                    self.language_dir(language),
                    latest.strftime('%Y%m%d'),
                    self._filename_template.substitute(
                        langcode=language,
                        date=latest.strftime('%Y%m%d'),
                        filename=filename,
                        filetype=self._config.get('Filetypes', filename))])

            scheme, netloc, path, query, anchor = urlparse.urlsplit(
                self._host)
            yield urlparse.urlunsplit((scheme, netloc, server_path, query,
                                       anchor))
