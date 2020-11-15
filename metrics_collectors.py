# -*- coding: utf-8 -*-

"""Classes for getting a list of companies and financial indicators company."""


from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import mean
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from utils import HtmlFetcher


class Companies:
    """Loads a page with a list of companies and finds tickers and stock prices."""

    def __init__(self, url, ignore_list):
        self._url = url
        self._companies_and_stocks = defaultdict(dict)
        self._ignore_list = ignore_list
        self._downloader = HtmlFetcher()

    def fetch(self):
        """Fetching list of companies."""
        html = self._downloader.fetch_page(self._url)
        soup = BeautifulSoup(html, 'lxml')
        tags_tr = soup.find('table', class_='simple-little-table trades-table').find_all('tr')
        # Thirst row skip because this is header
        for tag_tr in tags_tr[1:]:
            tds = tag_tr.find_all('td')
            ticker = tds[3].text
            if not tds[5].a or ticker in self._ignore_list:
                continue
            analysis_url = tds[5].a.get('href')
            stock_type = 'ordinary stock'
            # Defines working with preferred shares
            if len(ticker) == 5:
                ticker = ticker[:4]
                stock_type = 'preference stock'
            coast = self.__stock_coast(tds)
            self.list[ticker].update({stock_type: coast})
            self.list[ticker].update({'analysis_url': analysis_url})

    @property
    def list(self):
        return self._companies_and_stocks

    @staticmethod
    def __stock_coast(tds):
        """Getting float value from string."""
        try:
            return float(tds[6].text)
        except ValueError:
            return ''


class CompanyFinIndicators:
    """Loads a page with the financial statements of the company and finds financial indicators on it."""
    last_fin_year = None

    def __init__(self, ticker, base_url, analysis_url, ordinary_stock, preference_stock=None, default_val=''):
        if not self.last_fin_year:
            self.calc_last_fin_year()

        self._downloader = HtmlFetcher()

        self._count_reports = None
        self._fresh_report = False

        self._default_val = default_val
        self._ticker = ticker
        self._ordinary_stock = ordinary_stock
        self._preference_stock = preference_stock

        if analysis_url:
            self._url = urljoin(base_url, analysis_url)
        else:
            self._url = ''

    def fetch_fin_indicators(self):
        """Loads a page with the financial statements of the company and finds financial indicators on it."""
        indicators = CompanyIndicators(
            default_val=self._default_val,
            ticker=self._ticker,
            ordinary_stock=self._ordinary_stock,
            preference_stock=self._preference_stock
        )
        try:
            page = self._downloader.fetch_page(self._url)
        except ConnectionError:
            return indicators

        soup = BeautifulSoup(page, 'lxml')

        self._count_reports = self.__count_reports(soup)
        self._fresh_report = self.__check_fresh_report(soup)

        indicators.company_name = soup.find('h1').text.split('(')[0].strip()
        # чистая прибыль
        indicators.profit = self.__find_ltm_value_in_tags_td(soup, 'net_income')
        # средняя чистая прибыль
        indicators.average_profit = self.__find_mean_value_in_tags_td(soup, 'net_income')
        indicators.capitalization = self.__find_ltm_value_in_tags_td(soup, 'market_cap')
        indicators.enterprise_value = self.__find_ltm_value_in_tags_td(soup, 'ev')
        # Выручка
        indicators.proceeds = self.__find_ltm_value_in_tags_td(soup, 'revenue')
        indicators.roe = self.__find_ltm_value_in_tags_td(soup, 'roe')
        indicators.roa = self.__find_ltm_value_in_tags_td(soup, 'roa')
        indicators.dividends_ordinary = self.__find_last_value_in_tags_td(soup, 'dividend')
        indicators.dividends_preference = self.__find_last_value_in_tags_td(soup, 'dividend_pr')
        # Чистые активы
        indicators.clean_assets = self.__find_ltm_value_in_tags_td(soup, 'net_assets')
        # Балансовая стоимость
        indicators.book_value = self.__find_ltm_value_in_tags_td(soup, 'book_value')
        indicators.ebitda = self.__find_ltm_value_in_tags_td(soup, 'ebitda')
        indicators.net_debt = self.__find_ltm_value_in_tags_td(soup, 'net_debt')

        return indicators

    def __find_ltm_value_in_tags_td(self, soup, field):
        tds = self.__get_row_in_table(soup, field)
        if not tds:
            return self._default_val

        # Column number ltm 2 after the last column of the report self.count_reports + 2
        # The number of the last column with the report is equal to the number of reports self.count_reports
        num_ltm_column = self._count_reports + 2
        try:
            return self.__get_float_from_text(tds[num_ltm_column].text)
        except IndexError:
            return self._default_val

    def __find_mean_value_in_tags_td(self, soup, field):
        if not self._fresh_report:
            return self._default_val

        tds = self.__get_row_in_table(soup, field)
        if not tds:
            return self._default_val

        search_res = list()
        # The number of the last column with the report is equal to the number of reports self.count_reports
        for tag_td in tds[1:self._count_reports + 1]:
            indicator = self.__get_float_from_text(tag_td.text)
            if indicator is self._default_val:
                return self._default_val
            search_res.append(indicator)

        return round(mean(search_res), 2)

    def __find_last_value_in_tags_td(self, soup, field):
        if not self._fresh_report:
            return self._default_val

        tds = self.__get_row_in_table(soup, field)
        if not tds:
            return self._default_val
        # self.count_reports is also the last year report column number
        return self.__get_float_from_text(tds[self._count_reports].text)

    @staticmethod
    def __get_row_in_table(soup, field):
        try:
            return soup.find('tr', field=field).find_all('td')
        except AttributeError:
            return

    def __check_fresh_report(self, soup):
        """Checks the report for freshness."""
        try:
            year_last_report = int(soup.find('tr', class_='header_row').find_all('td')[self._count_reports].text)
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
            return self._default_val

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


@dataclass(repr=False, eq=False, order=False)
class CompanyIndicators:
    default_val: str = ''

    ticker: str = default_val
    ordinary_stock: str = default_val
    preference_stock: str = default_val

    company_name: str = default_val
    profit: str = default_val
    average_profit: str = default_val
    capitalization: str = default_val
    dividends_ordinary: str = default_val
    dividends_preference: str = default_val
    # стоимость предприятия - EV
    enterprise_value: str = default_val
    # чистые активы
    clean_assets: str = default_val
    # балансовая стоимость
    book_value: str = default_val
    ebitda: str = default_val
    net_debt: str = default_val
    proceeds: str = default_val
    roe: str = default_val
    roa: str = default_val

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
