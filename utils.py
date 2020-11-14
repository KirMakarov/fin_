# -*- coding: utf-8 -*-

"""Some auxiliary utils."""

import argparse

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

        response = self._session.get(url, headers=headers, timeout=5)
        if response.status_code != requests.codes.ok:
            raise BadResponseCode('Url: "{}". Response code:{}'.format(url, response.status_code))
        return response.text


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
