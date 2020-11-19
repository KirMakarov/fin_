import pytest

from uploaders import GoogleSpreadsheets, save_to_google_spreadsheets, save_to_file


@pytest.mark.parametrize('ordinary_stock, preference_stock, default_val, expected', [
    ('123', '456.4', '', 2),
    ('1', '456,6', '1', 1),
    ('4234', '4', '4', 1),
    ('9', '9', '9', 0),
])
def test_save_to_google_spreadsheets(mocker, ordinary_stock, preference_stock, default_val, expected):
    indicators = {'ASDF': mocker.Mock(ordinary_stock=ordinary_stock, preference_stock=preference_stock)}
    mocker.patch('uploaders.GoogleSpreadsheets.__init__', return_value=None)
    mocker.patch('uploaders.GoogleSpreadsheets.upload')
    add_line_cells = mocker.patch('uploaders.GoogleSpreadsheets.add_line_cells')
    save_to_google_spreadsheets(indicators, 'url', 'file_path', (1, 3, 5), default_val)
    assert add_line_cells.call_count == expected


@pytest.mark.parametrize('ordinary_stock, preference_stock, default_val, expected', [
    ('123', '456.4', '', 3),
    ('1', '456,6', '1', 2),
    ('4234', '4', '4', 2),
    ('9', '9', '9', 1),
])
def test_save_to_file(mocker, ordinary_stock, preference_stock, default_val, expected):
    indicators = {'ASDF': mocker.Mock(ordinary_stock=ordinary_stock, preference_stock=preference_stock)}
    writer = mocker.Mock()
    mocker.patch('uploaders.csv.writer', return_value=writer)
    mocker.patch('uploaders.open')
    save_to_file(indicators, 'file_path', default_val)
    assert writer.writerow.call_count == expected


@pytest.mark.parametrize('indicators, expected', [
    ([], 0),
    (['ASDF'], 1),
    (['ASDF', '23.6', 'qwerty', 'asd', 'zxc'], 5),
])
def test_google_spreadsheets(mocker, indicators, expected):
    worksheet = mocker.Mock()
    google_spreadsheets = mocker.Mock()
    google_spreadsheets.open_by_url.return_value.get_worksheet.return_value = worksheet
    mocker.patch('uploaders.gspread.authorize', return_value=google_spreadsheets)
    mocker.patch('uploaders.gspread.models')
    mocker.patch('uploaders.ServiceAccountCredentials')

    table = GoogleSpreadsheets('url', (1, 99, 5), 'file_path')
    table.add_line_cells(indicators)
    table.upload()
    assert len(worksheet.update_cells.call_args.args[0]) == expected
