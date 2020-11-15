# -*- coding: utf-8 -*-

"""Script for getting a list of companies and their financial indicators from https://smart-lab.ru/."""

import re

from uploaders import save_to_file, save_to_gsheet
from utils import get_arg_params, Logger
from metrics_collectors import Companies, CompanyFinIndicators


logger = Logger('scraper')
logger.set_logs('console')
logger.set_logs('file', logs_directory='.')


def controller():
    # Starting cell position (row, column) for upload data to google table
    start_cell = (3, 1)
    default_cell_val = str()

    companies_ignore_list = ['IMOEX', 'RU000A0JTXM2', 'RU000A0JUQZ6', 'RU000A0JVEZ0', 'RU000A0JVT35', 'GEMA', 'RUSI']
    companies_list_url = 'https://smart-lab.ru/q/shares/'
    site_url = 'https://smart-lab.ru/'

    params = get_arg_params()
    if not params['file_name'] and not all(params['gsheet']):
        logger.error('No option selected for saving results. \nSee help message: "scraper.py -h" \nExit from app.')
        raise ValueError('No option selected for saving results')

    companies = Companies(companies_list_url, companies_ignore_list)
    companies.fetch()

    logger.info('Fetch data has started.')
    companies_indicators = dict()
    for company, indicators in companies.list.items():
        ordinary_stock = indicators.get('ordinary stock', default_cell_val)
        preference_stock = indicators.get('preference stock', default_cell_val)
        company_information = CompanyFinIndicators(company, site_url, indicators['analysis_url'],
                                                   ordinary_stock, preference_stock, default_cell_val)
        companies_indicators[company] = company_information.fetch_fin_indicators()
        company_name = companies_indicators[company].company_name
        ticker = companies_indicators[company].ticker
        logger.info(f'Getting metrics {company_name} ({ticker})')

    logger.info('Data has fetched.')
    logger.info('-' * 60)

    if params['file_name']:
        # Replacing invalid characters in a file name
        file_name = re.sub(r'[\\/:*?"<>|+]', '', params['file_name'])
        save_to_file(companies_indicators, file_name, default_cell_val)
    if params['gsheet'][0]:
        save_to_gsheet(companies_indicators, *params['gsheet'], start_cell, default_cell_val)

    logger.close_logs('console')
    logger.close_logs('file')


if __name__ == '__main__':
    controller()
