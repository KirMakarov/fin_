from collections import OrderedDict
from datetime import date
from statistics import mean

import requests

from bs4 import BeautifulSoup


class BadResponseCode(ConnectionError):
    pass


class HtmlFetcher:
    @staticmethod
    def fetch_page(url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0',
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != requests.codes.ok:
            raise BadResponseCode('Url: "{}". Response code:{}'.format(url, response.status_code))
        return response.text


class FinancialIndicatorsCompanies(HtmlFetcher):
    ignore_list = ['IMOEX', 'RU000A0JTXM2', 'RU000A0JUQZ6', 'RU000A0JVEZ0', 'RU000A0JVT35', 'GEMA', 'RUSI']

    def __init__(self, url):
        self.url = url
        self.companies_and_stock = dict()

    def fetch_companies(self):
        html = self.fetch_page(self.url)
        soup = BeautifulSoup(html, 'lxml')
        tags_tr = soup.find('table', class_='simple-little-table trades-table').find_all('tr')
        for tag_tr in tags_tr:
            tds = tag_tr.find_all('td')
            try:
                tiker = tds[3].text
            except IndexError:
                continue
            stock_type = 'ordinary stock'
            if tiker in self.ignore_list:
                continue
            # Определяем работаем с привелигированными акциями
            if len(tiker) == 5:
                tiker = tiker[:4]
                stock_type = 'preference stock'
            coast = tds[6].text
            if not self.companies_and_stock.get(tiker):
                self.companies_and_stock[tiker] = dict()
            self.companies_and_stock[tiker].update({stock_type: coast})


class FinIndicatorsCompany(HtmlFetcher):
    last_fin_year = None

    def __init__(self, tiker, ordinary_stock, preference_stock=None):
        self.count_reports = None
        self.fresh_report = False

        self.tiker = tiker
        self.ordinary_stock = ordinary_stock
        self.preference_stock = preference_stock

        self.company_name = '-'
        self.profit = '-'
        self.average_profit = '-'
        self.capitalization = '-'
        self.dividends_ordinary = '-'
        self.dividends_preference = '-'
        self.ev = '-'
        # Чистые активы
        self.clean_assets = '-'
        # балансовая стоимость
        self.book_value = '-'

    def fetch_fin_indicators(self):
        url = f'https://smart-lab.ru/q/{self.tiker}/f/y/'
        # soup = BeautifulSoup(mock_request(self.tiker), 'lxml')
        soup = BeautifulSoup(self.fetch_page(url), 'lxml')

        self.count_reports = self.__count_reports(soup)
        self.fresh_report = self.__check_fresh_report(soup)

        self.company_name = soup.find('h1').text.split('(')[0].strip()
        # чистая прибыль
        self.profit = self.__find_value_in_tags_td(soup, 'net_income', 'ltm')
        # средняя чистая прибыль
        self.average_profit = self.__find_value_in_tags_td(soup, 'net_income', 'mean')
        self.capitalization = self.__find_value_in_tags_td(soup, 'market_cap', 'ltm')
        self.ev = self.__find_value_in_tags_td(soup, 'ev', 'ltm')
        self.dividends_ordinary = self.__find_value_in_tags_td(soup, 'dividend', 'last year')
        self.dividends_preference = self.__find_value_in_tags_td(soup, 'dividend_pr', 'last year')
        # Чистые активы
        self.clean_assets = self.__find_value_in_tags_td(soup, 'assets', 'ltm')
        # Балансовая стоимость
        self.book_value = self.__find_value_in_tags_td(soup, 'book_value', 'ltm')

    def __find_value_in_tags_td(self, soup, field, type_find_value):
        try:
            tds = soup.find('tr', field=field).find_all('td')
        except AttributeError:
            return '-'

        find_value = '-'

        if type_find_value == 'ltm':
            try:
                find_value = self.__get_float_from_text(tds[self.count_reports+2].text)
            except IndexError:
                find_value = '-'
        elif type_find_value == 'mean':
            if not self.fresh_report:
                return '-'
            search_res = []
            for tag_td in tds[1:1+self.count_reports]:
                indicator = self.__get_float_from_text(tag_td.text)
                if indicator == '-':
                    find_value = '-'
                    break
                search_res.append(self.__get_float_from_text(tag_td.text))
            else:
                find_value = round(mean(search_res), 2)
        elif type_find_value == 'last year':
            if not self.fresh_report:
                find_value = '-'
            else:
                find_value = self.__get_float_from_text(tds[self.count_reports].text)
        return find_value

    def __check_fresh_report(self, soup):
        try:
            year_last_report = int(soup.find('tr', class_='header_row').find_all('td')[self.count_reports].text)
        except ValueError:
            return False
        if self.last_fin_year > year_last_report:
            return False
        else:
            return True

    @staticmethod
    def __get_float_from_text(text):
        try:
            return float(text.strip().replace(' ', ''))
        except ValueError:
            return '-'

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
        # смотрим начиная с даты 1 июля. с 1,07,2020 ищем данные по 2019 г. Если их нет, то поля пустые.
        today = date.today()
        if today.month < date(1, 7, 1).month:
            cls.last_fin_year = today.year - 2
        else:
            cls.last_fin_year = today.year - 1

    @property
    def indicators_ordinary(self):
        return OrderedDict([
            ('company_name', self.company_name),
            ('tiker', self.tiker),
            ('stock', self.ordinary_stock),
            ('profit', self.profit),
            ('average_profit', self.average_profit),
            ('capitalization', self.capitalization),
            ('ev', self.ev),
            ('clean_assets', self.clean_assets),
            ('book_value', self.book_value),
            ('dividends', self.dividends_ordinary),
        ])

    @property
    def indicators_preference(self):
        return OrderedDict([
            ('company_name', self.company_name),
            ('tiker', self.tiker),
            ('stock', self.preference_stock),
            ('profit', self.profit),
            ('average_profit', self.average_profit),
            ('capitalization', self.capitalization),
            ('ev', self.ev),
            ('clean_assets', self.clean_assets),
            ('book_value', self.book_value),
            ('dividends', self.dividends_preference),
        ])


def save_to_file(companies_indicators, file_patn_and_name):
    print("Save to file.")
    with open(file_patn_and_name, 'w') as result:
        header = False
        for indicators in companies_indicators.items():
            if not header:
                result.write('; '.join(indicators.indicators_ordinary))
                result.write('\n')
                header = True

            if indicators.ordinary_stock != '-':
                line = '; '.join([str(elem) for elem in indicators.indicators_ordinary.values()])
                result.write(line)
                result.write('\n')

            if indicators.preference_stock != '-':
                line = '; '.join([str(elem) for elem in indicators.indicators_preference.values()])
                result.write(line)
                result.write('\n')


def controller():
    companies_indicators = dict()
    FinIndicatorsCompany.calc_last_fin_year()

    companies = FinancialIndicatorsCompanies('https://smart-lab.ru/q/shares/')
    companies.fetch_companies()

    print('Start fetch data.\n')
    for company, costs_stoks in companies.companies_and_stock.items():
        ordinary_stock = costs_stoks.get('ordinary stock', '-')
        preference_stock = costs_stoks.get('preference stock', '-')
        companies_indicators[company] = FinIndicatorsCompany(company, ordinary_stock, preference_stock)
        companies_indicators[company].fetch_fin_indicators()

        print(companies_indicators[company].company_name, companies_indicators[company].tiker)

    save_to_file(companies_indicators, 'fin_indicators_companies.csv')


if __name__ == '__main__':
    controller()
