# Scraper financial indicators companies

Script fetch from https://smart-lab.ru/ companies and its financial indicators:
* company_name; 
* tiker; 
* stock ordinary; 
* dividends ordinary; 
* stock preference; 
* dividends preference; 
* average profit; 
* capitalization; 
* ev; 
* clean_assets; 
* book_value.

Results save on disk to .csv file or upload to google table.

## Requirements
* Python 3.5 and or higher
* Python packages. For install run command from command line:
```sh
pip3 install -r requirements.txt 
```
* Also for upload to google sheet, need get json key file.
How to get the JSON keyfile:
following the link https://gspread.readthedocs.io/en/latest/oauth2.html
and read the paragraph “Using signed credentials” steps 1-3.

## Run
```sh
python3.5 scraber.py [-g link_google_table, json_keyfile] [-f file_name.csv]
```
### Optional arguments:
Argument       | Description
|-------------:|:---------------
-h, --help     |    show help message and exit
-g             |    Link to google sheet and file name JSON keyfile from google.How get JSON keyfile read paragraph Using Signed Credentials path 1-3 from link:How to get the JSON keyfile: read the paragraph “Using signed credentials” steps 1-3, following the link: https://gspread.readthedocs.io/en/latest/oauth2.html
-f             |    Save result to file. Need write file name. Example: "fin_indicators_companies.csv"

### Examples
```sh
python3.5 scraber.py -f result.csv
```
```sh
python3.5 scraber.py -g https://docs.google.com/spreadsheets/d/123qwe-zxc sheets-py-123a4q56.json
```

## TODO
* [x] select output .csv file name
* [x] save results to google sheet
* [x] add config file
* [ ] add progress bar
* [ ] add method for calculate some new indicators
* [ ] download html file in one connection
* [ ] async html fetcher