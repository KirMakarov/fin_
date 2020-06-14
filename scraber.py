# -*- coding: utf-8 -*-

"""Script fetch from https://smart-lab.ru/ companies and its financial indicators"""

import argparse
import re

from collections import OrderedDict, defaultdict
from datetime import date
from statistics import mean
from urllib.parse import urljoin

import gspread
import requests

from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials


class BadResponseCode(ConnectionError):
    pass


class HtmlFetcher:
    """HTML file downloader"""
    @staticmethod
    def fetch_page(url):
        """Download html page and return text from this page."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0',
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != requests.codes.ok:
            raise BadResponseCode('Url: "{}". Response code:{}'.format(url, response.status_code))
        return response.text


class FinancialIndicatorsCompanies:
    """Loads a page with a list of companies and finds tickers and stock prices."""
    def __init__(self, url, ignore_list):
        self.url = url
        self.companies_and_stock = defaultdict(dict)
        self.ignore_list = ignore_list
        self.downloader = HtmlFetcher()

    def fetch_companies(self):
        html = self.downloader.fetch_page(self.url)
        soup = BeautifulSoup(html, 'lxml')
        tags_tr = soup.find('table', class_='simple-little-table trades-table').find_all('tr')
        # Thirst row skip because this is header
        for tag_tr in tags_tr[1:]:
            tds = tag_tr.find_all('td')
            tiker = tds[3].text
            if not tds[5].a or tiker in self.ignore_list:
                continue
            analysis_url = tds[5].a.get('href')
            stock_type = 'ordinary stock'
            # Defines working with preferred shares
            if len(tiker) == 5:
                tiker = tiker[:4]
                stock_type = 'preference stock'
            coast = tds[6].text
            self.companies_and_stock[tiker].update({stock_type: coast})
            self.companies_and_stock[tiker].update({'analysis_url': analysis_url})


class FinIndicatorsCompany:
    """Loads a page with the financial statements of the company and finds financial indicators on it."""
    last_fin_year = None

    def __init__(self, tiker, base_url, analysis_url, ordinary_stock, preference_stock=None, default_val=''):
        self.downloader = HtmlFetcher()
        self.count_reports = None
        self.fresh_report = False
        self.default_val = default_val

        self.tiker = tiker
        if analysis_url:
            self.url = urljoin(base_url, analysis_url)
        else:
            self.url = ''
        self.ordinary_stock = ordinary_stock
        self.preference_stock = preference_stock

        self.company_name = self.profit = self.average_profit = self.capitalization = default_val
        self.dividends_ordinary = self.dividends_preference = default_val
        # стоимость предприятия - EV | Чистые активы | балансовая стоимость
        self.enterprise_value = self.clean_assets = self.book_value = default_val

    def fetch_fin_indicators(self):
        """Loads a page with the financial statements of the company and finds financial indicators on it."""
        try:
            page = self.downloader.fetch_page(self.url)
        except BadResponseCode:
            return

        soup = BeautifulSoup(page, 'lxml')

        self.count_reports = self.__count_reports(soup)
        self.fresh_report = self.__check_fresh_report(soup)

        self.company_name = soup.find('h1').text.split('(')[0].strip()
        # чистая прибыль
        self.profit = self.__find_ltm_value_in_tags_td(soup, 'net_income')
        # средняя чистая прибыль
        self.average_profit = self.__find_mean_value_in_tags_td(soup, 'net_income')
        self.capitalization = self.__find_ltm_value_in_tags_td(soup, 'market_cap')
        self.enterprise_value = self.__find_ltm_value_in_tags_td(soup, 'ev')
        self.dividends_ordinary = self.__find_last_value_in_tags_td(soup, 'dividend')
        self.dividends_preference = self.__find_last_value_in_tags_td(soup, 'dividend_pr')
        # Чистые активы
        self.clean_assets = self.__find_ltm_value_in_tags_td(soup, 'assets')
        # Балансовая стоимость
        self.book_value = self.__find_ltm_value_in_tags_td(soup, 'book_value')

    def __find_ltm_value_in_tags_td(self, soup, field):
        tds = self.__get_row_in_table(soup, field)
        if not tds:
            return self.default_val

        # Column number ltm 2 after the last column of the report self.count_reports + 2
        # The number of the last column with the report is equal to the number of reports self.count_reports
        num_ltm_column = self.count_reports + 2
        try:
            return self.__get_float_from_text(tds[num_ltm_column].text)
        except IndexError:
            return self.default_val

    def __find_mean_value_in_tags_td(self, soup, field):
        if not self.fresh_report:
            return self.default_val

        tds = self.__get_row_in_table(soup, field)
        if not tds:
            return self.default_val

        search_res = list()
        # The number of the last column with the report is equal to the number of reports self.count_reports
        for tag_td in tds[1:self.count_reports + 1]:
            indicator = self.__get_float_from_text(tag_td.text)
            if indicator is self.default_val:
                return self.default_val
            search_res.append(indicator)

        return round(mean(search_res), 2)

    def __find_last_value_in_tags_td(self, soup, field):
        if not self.fresh_report:
            return self.default_val

        tds = self.__get_row_in_table(soup, field)
        if not tds:
            return self.default_val
        # self.count_reports is also the last year report column number
        return self.__get_float_from_text(tds[self.count_reports].text)

    @staticmethod
    def __get_row_in_table(soup, field):
        try:
            return soup.find('tr', field=field).find_all('td')
        except AttributeError:
            return

    def __check_fresh_report(self, soup):
        """Checks the report for freshness."""
        try:
            year_last_report = int(soup.find('tr', class_='header_row').find_all('td')[self.count_reports].text)
        except ValueError:
            return False

        if self.last_fin_year > year_last_report:
            return False
        else:
            return True

    def __get_float_from_text(self, text):
        try:
            return float(text.strip().replace(' ', ''))
        except ValueError:
            return self.default_val

    @staticmethod
    def __count_reports(soup):
        """Counts the number of financial reports"""
        tags_td = soup.find('tr', class_='header_row').find_all('td')
        count = 0
        for tag in tags_td:
            if tag.text.isdigit():
                count += 1
        return count

    @classmethod
    def calc_last_fin_year(cls):
        """Last fiscal year calculate. Year select about 1 july."""
        today = date.today()
        if today.month < date(1, 7, 1).month:
            cls.last_fin_year = today.year - 2
        else:
            cls.last_fin_year = today.year - 1

    @property
    def indicators_ordinary(self):
        """Return order dict with finance indicators and ordinary stock"""
        return OrderedDict([
            ('company name', self.company_name),
            ('tiker', self.tiker),
            ('stock', self.ordinary_stock),
            ('profit', self.profit),
            ('average profit', self.average_profit),
            ('capitalization', self.capitalization),
            ('enterprise value', self.enterprise_value),
            ('clean assets', self.clean_assets),
            ('book value', self.book_value),
            ('dividends', self.dividends_ordinary),
        ])

    @property
    def indicators_preference(self):
        """Return order dict with finance indicators and preference stock"""
        return OrderedDict([
            ('company name', self.company_name),
            # + 'P" because this preference stock
            ('tiker', self.tiker + 'P'),
            ('stock', self.preference_stock),
            ('profit', self.profit),
            ('average profit', self.average_profit),
            ('capitalization', self.capitalization),
            ('enterprise value', self.enterprise_value),
            ('clean assets', self.clean_assets),
            ('book value', self.book_value),
            ('dividends', self.dividends_preference),
        ])


def save_to_file(companies_indicators, file_path_and_name, default_cell_val=str()):
    """Save file on disk"""
    print("Save to file.")
    with open(file_path_and_name, 'w') as result:
        header = False
        for indicators in companies_indicators.values():
            if not header:
                result.write('; '.join(indicators.indicators_ordinary))
                result.write('\n')
                header = True

            if indicators.ordinary_stock != default_cell_val:
                line = '; '.join([str(elem) for elem in indicators.indicators_ordinary.values()])
                result.write(line)
                result.write('\n')

            if indicators.preference_stock != default_cell_val:
                line = '; '.join([str(elem) for elem in indicators.indicators_preference.values()])
                result.write(line)
                result.write('\n')
    print("Write to file complete.")


class Gtable:
    """Class for upload cell list to google table"""
    def __init__(self, url_table, num_list_table, json_key_file, start_cell):
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(json_key_file, scope)
        gspr = gspread.authorize(credentials)
        wsh = gspr.open_by_url(url_table)
        self.worksheet = wsh.get_worksheet(num_list_table)
        self.cell_list = []
        self.current_row, self.current_column = start_cell

    def upload(self):
        """Upload cell list to google table"""
        self.worksheet.update_cells(self.cell_list)

    def add_line_cells(self, company_indicators):
        """Adds cells in order on one line. And increment the number current line table by 1"""
        self.cell_list += [
            gspread.models.Cell(self.current_row, num_col, value=param)
            for num_col, param in enumerate(company_indicators.values(), start=self.current_column)
        ]
        self.current_row += 1


def save_to_gsheet(companies_indicators, table_url, google_key_file, start_cell, default_cell_val):
    """Save data to goggle table."""
    print('Create table')
    num_list = 1
    table = Gtable(table_url, num_list, google_key_file, start_cell)
    for indicators in companies_indicators.values():
        if indicators.ordinary_stock != default_cell_val:
            table.add_line_cells(indicators.indicators_ordinary)
        if indicators.preference_stock != default_cell_val:
            table.add_line_cells(indicators.indicators_preference)
    print('Upload table')
    table.upload()
    print("Upload data to goggle table complete.")


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


def controller():
    # Starting cell position (row, column) for upload data to google table
    start_cell = (2, 5)
    default_cell_val = str()

    companies_ignore_list = ['IMOEX', 'RU000A0JTXM2', 'RU000A0JUQZ6', 'RU000A0JVEZ0', 'RU000A0JVT35', 'GEMA', 'RUSI']
    companies_list_url = 'https://smart-lab.ru/q/shares/'
    site_url = 'https://smart-lab.ru/'

    params = get_arg_params()
    if not params['file_name'] and not all(params['gsheet']):
        print('No option selected for saving results. \nSee help message: "scraber.py -h" \nExit from app.')
        exit(1)

    companies_indicators = dict()
    FinIndicatorsCompany.calc_last_fin_year()

    companies = FinancialIndicatorsCompanies(companies_list_url, companies_ignore_list)
    companies.fetch_companies()

    print('Start fetch data.\n')
    for company, costs_stoks in companies.companies_and_stock.items():
        ordinary_stock = costs_stoks.get('ordinary stock', default_cell_val)
        preference_stock = costs_stoks.get('preference stock', default_cell_val)
        companies_indicators[company] = FinIndicatorsCompany(company, site_url, costs_stoks['analysis_url'],
                                                             ordinary_stock, preference_stock, default_cell_val)
        companies_indicators[company].fetch_fin_indicators()

        print(companies_indicators[company].company_name, companies_indicators[company].tiker)

    if params['file_name']:
        # Replacing invalid characters in a file name
        file_name = re.sub(r'[\\/:*?"<>|+]', '', params['file_name'])
        save_to_file(companies_indicators, file_name, default_cell_val)
    if params['gsheet'][0]:
        save_to_gsheet(companies_indicators, *params['gsheet'], start_cell, default_cell_val)


if __name__ == '__main__':
    controller()
