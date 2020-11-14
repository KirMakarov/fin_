# -*- coding: utf-8 -*-

"""Uploaders to file and to google tables."""

import gspread

from oauth2client.service_account import ServiceAccountCredentials


class Gtable:
    """Class for upload cell list to google table."""
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
    num_list = 3
    table = Gtable(table_url, num_list, google_key_file, start_cell)
    for indicators in companies_indicators.values():
        if indicators.ordinary_stock != default_cell_val:
            table.add_line_cells(indicators.indicators_ordinary)
        if indicators.preference_stock != default_cell_val:
            table.add_line_cells(indicators.indicators_preference)
    print('Upload table')
    table.upload()
    print("Upload data to google table complete.")


def save_to_file(companies_indicators, file_path_and_name, default_cell_val=str()):
    """Save file on disk."""
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
