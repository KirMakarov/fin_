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

Results save on disk to .csv file ''fin_indicators_companies.csv".

## Requirements
* Python 3.5 and or higher
* Python packages. For install use command:
```sh
pip3 install -r requirements.txt 
```

## Run
```sh
python3.5 scraber.py
```

## TODO
* select output .csv file name
* save results to google sheet
* add config file
* download html file in one connection
* async html fetcher 