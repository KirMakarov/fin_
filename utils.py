# -*- coding: utf-8 -*-

"""Some auxiliary utils."""

import argparse
import os

from logging import Formatter, getLogger, FileHandler, StreamHandler
from logging import INFO, DEBUG

import requests


class BadResponseCode(ConnectionError):
    """Bad response code"""


class HtmlFetcher:
    """HTML file downloader."""
    _session = None

    def __init__(self):
        if not self._session:
            __class__._session = requests.Session()

    def fetch_page(self, url):
        """Download html page and return text from this page."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0',
        }

        try:
            response = self._session.get(url, headers=headers, timeout=5)
        except requests.exceptions:
            raise ConnectionError(f'Failed to establish connection with "{url}"')
        if response.status_code != requests.codes.ok:
            raise BadResponseCode(f'Url: "{url}". Response code:{response.status_code}')
        return response.text


class Logger:
    """Writes system state to log files."""

    def __init__(self, name=None):
        self.__name = name
        self.__loggers = {'file': self.__file_logger,
                          'console': self.__console_logger
                          }
        self.__log_level = {'info': INFO, 'debug': DEBUG}
        self.__modes = []
        self.__logs_directory = ''
        self.__common_log_handler = None
        self.__console_log_handler = None
        self.__log_format = None

        self.__logger = getLogger(self.__name)

        self.info = self.__logger.info
        self.debug = self.__logger.debug
        self.warning = self.__logger.warning
        self.error = self.__logger.error
        self.critical = self.__logger.critical

    def set_logs(self, mode=None, message_level='info', logs_directory=None):
        """Set logger handlers."""
        if mode not in self.__loggers:
            raise ValueError('Mode "{mode}" is not support')
        self.__modes.append(mode)
        if mode == 'file':
            if not logs_directory:
                raise ValueError('"logs_path" should not be None')
            self.__logs_directory = logs_directory

        self.__logger.setLevel(self.__log_level[message_level])

        message_format = '%(levelname)-8s %(asctime)s %(message)-60s (%(filename)s:%(lineno)d)'
        self.__log_format = Formatter(fmt=message_format, datefmt="%y-%m-%d %H:%M:%S")
        self.__loggers.get(mode).__call__()

    def __file_logger(self):
        """Create and start loggers file handler."""
        log_file = f'{self.__name}.log'
        log_file_path = os.path.join(self.__logs_directory, log_file)

        # Existing log rewriting
        if os.path.exists(log_file_path):
            os.remove(log_file_path)

        self.__common_log_handler = FileHandler(log_file_path, mode='w', encoding='utf-8')
        self.__common_log_handler.setFormatter(self.__log_format)

        self.__logger.addHandler(self.__common_log_handler)

    def __console_logger(self):
        """Create and start loggers console handler."""
        self.__console_log_handler = StreamHandler()
        self.__console_log_handler.setFormatter(self.__log_format)
        self.__logger.addHandler(self.__console_log_handler)

    def close_logs(self, mode=None):
        """Close logger handlers."""
        if mode not in self.__modes:
            return
        if mode == 'file':
            self.__common_log_handler.close()
            self.__logger.removeHandler(self.__common_log_handler)
        elif mode == 'console':
            self.__console_log_handler.close()
            self.__logger.removeHandler(self.__console_log_handler)
        self.__modes.remove(mode)


def get_arg_params():
    """Startup key getting. Get command line arguments and return dict with startup parameters."""
    cmd_parser = argparse.ArgumentParser(
        description='Script fetch from https://smart-lab.ru/ companies and its financial indicators.'
    )
    cmd_parser.add_argument('-g',
                            dest='gsheet',
                            nargs=2,
                            default=[None, None],
                            help='Link to google sheet and file name JSON keyfile from google. '
                                 'Details see in the README.MD'
                            )
    cmd_parser.add_argument('-f',
                            dest='file_name',
                            default='',
                            help='Save result to file. Need write file name. Example: "fin_indicators_companies.csv"'
                            )
    return vars(cmd_parser.parse_args())
