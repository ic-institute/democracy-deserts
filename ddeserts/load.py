"""Load and parse CSV data"""
from csv import DictReader
from itertools import groupby

from pandas import DataFrame

from os.path import basename
from os.path import join

from .parse import parse_cvap_row


# translate single-race lntitle values to three-letter prefixes, and
# "Total" to no prefix
LN_PREFIXES = {
    'Total': '',
    'American Indian or Alaska Native Alone': 'ind_',
    'Asian Alone': 'asn_',
    'Black or African American Alone': 'blk_',
    'Native Hawaiian or Other Pacific Islander Alone': 'pac_',
    'White Alone': 'wht_',
    'Hispanic or Latino': 'his_',
}


CVAP_DATA_DIR = 'data/census/CVAP_2015-2019_ACS_csv_files'
CHARTER_CITIES_FILE = 'data/cacities/charter-cities.txt'


def load_charter_cities():
    with open(CHARTER_CITIES_FILE) as f:
        return { line.strip() for line in f }


def load_cvap_data(name, *, pre_filter=None, filter=None):
    path = join(CVAP_DATA_DIR, name + '.csv')

    rows = read_cvap_csv(path, pre_filter=pre_filter, filter=filter)

    records = rows_to_records(rows)

    df = DataFrame.from_records(records, index=['table', 'line'])

    # fix data types
    df['tot_moe'] = df['tot_moe'].astype('int')
    df['adu_moe'] = df['adu_moe'].astype('int')
    df['cvap_moe'] = df['cvap_moe'].astype('int')
    df['cit_moe'] = df['cit_moe'].astype('int')

    return df


def rows_to_records(csv_rows):
    """Turn groups of rows for the same geography into a single record."""
    for _, rows in groupby(csv_rows, lambda r: r['geoid']):
        result = None

        for row in rows:
            if result is None:
                # values that are the same for all rows in the group
                result = {
                    k: v for k, v in row.items()
                    if k in ('geoid', 'geoname', 'line', 'table')
                }

            # look up the prefix for whichever ethnic/racial group this
            # row is about (or '' for the Total row)
            prefix = LN_PREFIXES.get(row['lntitle'])
            if prefix is None:
                continue

            # e.g. if prefix is 'blk_', transform 'tot_est' to 'blk_tot_est'
            for k, v in row.items():
                if '_' in k:
                    result[prefix + k] = int(v)  # values are always numbers

        yield result


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
