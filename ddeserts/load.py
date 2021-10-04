"""Load and parse CSV data"""
from csv import DictReader

from pandas import DataFrame

from os.path import basename
from os.path import join

from .parse import parse_cvap_row


CVAP_DATA_DIR = 'data/census/CVAP_2015-2019_ACS_csv_files'
CHARTER_CITIES_FILE = 'data/cacities/charter-cities.txt'


def load_charter_cities():
    with open(CHARTER_CITIES_FILE) as f:
        return { line.strip() for line in f }


def load_cvap_data(name, *, pre_filter=None, filter=None):
    path = join(CVAP_DATA_DIR, name + '.csv')

    rows = list(read_cvap_csv(path, pre_filter=pre_filter, filter=filter))

    df = DataFrame.from_records(rows, index=['table', 'line'])

    # fix data types
    df['tot_moe'] = df['tot_moe'].astype('int')
    df['adu_moe'] = df['adu_moe'].astype('int')
    df['cvap_moe'] = df['cvap_moe'].astype('int')
    df['cit_moe'] = df['cit_moe'].astype('int')

    return df


def read_cvap_csv(path, *, pre_filter=None, filter=None):
    # e.g. 'Place'
    table = basename(path).rsplit('.', 1)[0]

    with open(path, newline='', encoding='latin-1') as f:

        line_num = 0

        def pre_filter_lines():
            # pre-filter the lines, tracking line num
            nonlocal line_num

            for i, line in enumerate(f):
                if i == 0 or not pre_filter or pre_filter(line):
                    yield line
                line_num = i + 1  # used below

        reader = DictReader(pre_filter_lines())

        for row in reader:
            parsed_row = parse_cvap_row(row)

            row['line'] = line_num
            row['table'] = table

            if not filter or filter(parsed_row):
                yield parsed_row
