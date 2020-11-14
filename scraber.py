# -*- coding: utf-8 -*-

"""Script for getting a list of companies and their financial indicators from https://smart-lab.ru/."""

import re

from uploaders import save_to_file, save_to_gsheet
from utils import get_arg_params
from metric_collectors import FinancialIndicatorsCompanies, FinIndicatorsCompany


def controller():
    # Starting cell position (row, column) for upload data to google table
    start_cell = (3, 1)
    default_cell_val = str()

    companies_ignore_list = ['IMOEX', 'RU000A0JTXM2', 'RU000A0JUQZ6', 'RU000A0JVEZ0', 'RU000A0JVT35', 'GEMA', 'RUSI']
    companies_list_url = 'https://smart-lab.ru/q/shares/'
    site_url = 'https://smart-lab.ru/'

    params = get_arg_params()
    if not params['file_name'] and not all(params['gsheet']):
        print('No option selected for saving results. \nSee help message: "scraber.py -h" \nExit from app.')
        raise ValueError('No option selected for saving results')

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

        print(companies_indicators[company].company_name, '-', companies_indicators[company].ticker)

    print('\nData fetched.\n')
    print('- ' * 25)

    if params['file_name']:
        # Replacing invalid characters in a file name
        file_name = re.sub(r'[\\/:*?"<>|+]', '', params['file_name'])
        save_to_file(companies_indicators, file_name, default_cell_val)
    if params['gsheet'][0]:
        save_to_gsheet(companies_indicators, *params['gsheet'], start_cell, default_cell_val)


if __name__ == '__main__':
    controller()
