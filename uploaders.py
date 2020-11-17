# -*- coding: utf-8 -*-

"""Uploaders to file and to google tables."""


import csv

import gspread

from oauth2client.service_account import ServiceAccountCredentials

from utils import Logger


logger = Logger('scraper')


class GoogleSpreadsheets:
    """Class for upload cell list to google table."""
    def __init__(self, url_table, start_position, json_key_file):
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(json_key_file, scope)
        google_spreadsheets = gspread.authorize(credentials)
        worksheets = google_spreadsheets.open_by_url(url_table)
        num_list_table, self._current_row, self._current_column = start_position
        self._worksheet = worksheets.get_worksheet(num_list_table)
        self._cell_list = []

    def upload(self):
        """Upload cell list to google table"""
        self._worksheet.update_cells(self._cell_list)

    def add_line_cells(self, company_indicators):
        """Adds cells in order on one line. And increment the number current line table by 1"""
        self._cell_list += [
            gspread.models.Cell(self._current_row, num_col, value=param)
            for num_col, param in enumerate(company_indicators, start=self._current_column)
        ]
        self._current_row += 1


def save_to_google_spreadsheets(companies_indicators, table_url, google_key_file, start_position, default_cell_val=''):
    """Save data to goggle table."""
    logger.info('Create table')

    table = GoogleSpreadsheets(table_url, start_position, google_key_file)
    for indicators in companies_indicators.values():
        if indicators.ordinary_stock != default_cell_val:
            table.add_line_cells(indicators.indicators_ordinary.values())
        if indicators.preference_stock != default_cell_val:
            table.add_line_cells(indicators.indicators_preference.values())
    logger.info('Upload table')
    table.upload()
    logger.info("Upload data to google spreadsheets complete.")


def save_to_file(companies_indicators, path, default_cell_val=''):
    """Save file on disk."""
    logger.info("Save to file.")
    with open(path, "w", newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        header = False
        for indicators in companies_indicators.values():
            if not header:
                writer.writerow(indicators.indicators_ordinary)
                header = True

            if indicators.ordinary_stock != default_cell_val:
                writer.writerow(indicators.indicators_ordinary.values())

            if indicators.preference_stock != default_cell_val:
                writer.writerow(indicators.indicators_preference.values())
    logger.info("Write to file complete.")
