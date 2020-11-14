# -*- coding: utf-8 -*-

"""Classes for getting a list of companies and financial indicators company."""


from collections import OrderedDict, defaultdict
from datetime import date
from statistics import mean
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from utils import BadResponseCode, HtmlFetcher


class FinancialIndicatorsCompanies:
    """Loads a page with a list of companies and finds tickers and stock prices."""
    def __init__(self, url, ignore_list):
        self.url = url
        self.companies_and_stock = defaultdict(dict)
        self.ignore_list = ignore_list
        self.downloader = HtmlFetcher()

    def fetch_companies(self):
        """Fetching list of companies."""
        html = self.downloader.fetch_page(self.url)
        soup = BeautifulSoup(html, 'lxml')
        tags_tr = soup.find('table', class_='simple-little-table trades-table').find_all('tr')
        # Thirst row skip because this is header
        for tag_tr in tags_tr[1:]:
            tds = tag_tr.find_all('td')
            ticker = tds[3].text
            if not tds[5].a or ticker in self.ignore_list:
                continue
            analysis_url = tds[5].a.get('href')
            stock_type = 'ordinary stock'
            # Defines working with preferred shares
            if len(ticker) == 5:
                ticker = ticker[:4]
                stock_type = 'preference stock'
            coast = self.__stock_coast(tds)
            self.companies_and_stock[ticker].update({stock_type: coast})
            self.companies_and_stock[ticker].update({'analysis_url': analysis_url})

    @staticmethod
    def __stock_coast(tds):
        """Getting float value from string."""
        try:
            return float(tds[6].text)
        except ValueError:
            return ''


class FinIndicatorsCompany:
    """Loads a page with the financial statements of the company and finds financial indicators on it."""
    last_fin_year = None

    def __init__(self, ticker, base_url, analysis_url, ordinary_stock, preference_stock=None, default_val=''):
        self.downloader = HtmlFetcher()
        self.count_reports = None
        self.fresh_report = False
        self.default_val = default_val

        self.ticker = ticker
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
        self.ebitda = self.net_debt = default_val
        self.proceeds = self.roe = self.roa = default_val

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
        # Выручка
        self.proceeds = self.__find_ltm_value_in_tags_td(soup, 'revenue')
        self.roe = self.__find_ltm_value_in_tags_td(soup, 'roe')
        self.roa = self.__find_ltm_value_in_tags_td(soup, 'roa')
        self.dividends_ordinary = self.__find_last_value_in_tags_td(soup, 'dividend')
        self.dividends_preference = self.__find_last_value_in_tags_td(soup, 'dividend_pr')
        # Чистые активы
        self.clean_assets = self.__find_ltm_value_in_tags_td(soup, 'net_assets')
        # Балансовая стоимость
        self.book_value = self.__find_ltm_value_in_tags_td(soup, 'book_value')
        self.ebitda = self.__find_ltm_value_in_tags_td(soup, 'ebitda')
        self.net_debt = self.__find_ltm_value_in_tags_td(soup, 'net_debt')

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
        return True

    def __get_float_from_text(self, text):
        """Getting float value from string."""
        try:
            return float(text.strip().replace(' ', '').replace('%', ''))
        except ValueError:
            return self.default_val

    @staticmethod
    def __count_reports(soup):
        """Counts the number of financial reports."""
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
        """Return order dict with finance indicators and ordinary stock."""
        return OrderedDict([
            ('company name', self.company_name),
            ('ticker', self.ticker),
            ('stock', self.ordinary_stock),
            ('profit', self.profit),
            ('average profit', self.average_profit),
            ('capitalization', self.capitalization),
            ('enterprise value', self.enterprise_value),
            ('clean assets', self.clean_assets),
            ('book value', self.book_value),
            ('ebitda', self.ebitda),
            ('net_debt', self.net_debt),
            ('dividends', self.dividends_ordinary),
            ('proceeds', self.proceeds),
            ('roe', self.roe),
            ('roa', self.roa),
        ])

    @property
    def indicators_preference(self):
        """Return order dict with finance indicators and preference stock."""
        return OrderedDict([
            ('company name', self.company_name),
            # + 'P" because this preference stock
            ('ticker', self.ticker + 'P'),
            ('stock', self.preference_stock),
            ('profit', self.profit),
            ('average profit', self.average_profit),
            ('capitalization', self.capitalization),
            ('enterprise value', self.enterprise_value),
            ('clean assets', self.clean_assets),
            ('book value', self.book_value),
            ('ebitda', self.ebitda),
            ('net_debt', self.net_debt),
            ('dividends', self.dividends_preference),
            ('proceeds', self.proceeds),
            ('roe', self.roe),
            ('roa', self.roa),
        ])
