"""Load and parse CSV data"""
from csv import DictReader
from itertools import groupby

from pandas import DataFrame

from os.path import basename
from os.path import join

from .annotate import LN_PREFIXES
from .annotate import moe_of_sum
from .parse import parse_age_sex_cit_row
from .parse import parse_cvap_row
from .parse import parse_felon_disf_row


AGE_SEX_CIT_DATA_PATH = (
    'data/census/ACSDT1Y2022.B05003/ACSDT1Y2022.B05003-Data.csv')
CVAP_DATA_DIR = 'data/census/CVAP_2017-2021_ACS_csv_files'
CHARTER_CITIES_FILE = 'data/cacities/charter-cities.txt'
FELON_DISF_PATH_PATTERN = 'data/tsp/2022-felon disenfranchisement-{0}.csv'


def load_age_sex_cit_data():
    """Load data from the B05033 (Age, Sex, Nativity, and Citizenship)
    CSV file.

    Return it as a stream of rows
    """
    rows = read_age_sex_cit_csv(AGE_SEX_CIT_DATA_PATH)
    cvap_rows = [age_sex_cit_row_to_cvap(row) for row in rows]

    df = DataFrame.from_records(cvap_rows)

    # fix data types
    df['tot_moe'] = df['tot_moe'].astype('int')
    df['adu_moe'] = df['adu_moe'].astype('int')
    df['cvap_moe'] = df['cvap_moe'].astype('int')
    df['cit_moe'] = df['cit_moe'].astype('int')

    return df


def load_charter_cities():
    with open(CHARTER_CITIES_FILE) as f:
        return { line.strip() for line in f }


def load_cvap_data(name, *, pre_filter=None):
    path = join(CVAP_DATA_DIR, name + '.csv')

    rows = read_cvap_csv(path, pre_filter=pre_filter)

    records = rows_to_records(rows)

    df = DataFrame.from_records(records, index=['table', 'line'])

    # fix data types
    df['tot_moe'] = df['tot_moe'].astype('int')
    df['adu_moe'] = df['adu_moe'].astype('int')
    df['cvap_moe'] = df['cvap_moe'].astype('int')
    df['cit_moe'] = df['cit_moe'].astype('int')

    return df


def load_felon_disf_data(population='all'):
    path = FELON_DISF_PATH_PATTERN.format(population)

    rows = read_felon_disf_csv(path)
    cvap_rows = [felon_disf_row_to_cvap(row) for row in rows]

    df = DataFrame.from_records(cvap_rows)

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


def read_age_sex_cit_csv(path):

    with open(path, newline='', encoding='latin-1') as f:

        f.readline()  # skip the first line

        reader = DictReader(f)

        for row in reader:
            parsed_row = parse_age_sex_cit_row(row)

            yield parsed_row


def read_cvap_csv(path, *, pre_filter=None):
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

            yield parsed_row


def read_felon_disf_csv(path):
     with open(path, newline='', encoding='latin-1') as f:
        reader = DictReader(f)

        for row in reader:
            parsed_row = parse_felon_disf_row(row)

            yield parsed_row


def age_sex_cit_row_to_cvap(row):
    """Convert a row from the B05033 (Age, Sex, Nativity, and Citizenship)
    data into data matching the CVAP table. Should contain the following
    fields:

    line
    geoname
    geotype (always 'state')
    tot_est
    tot_moe
    adu_est
    adu_moe
    cit_est
    cit_moe
    cvap_est
    cvap_moe
    """
    geoname = ''
    geotype = 'state'
    tot_est = 0
    tot_moe = 0
    adu_ests = []
    adu_moes = []
    cit_ests = []
    cit_moes = []
    cvap_ests = []
    cvap_moes = []

    for k, v in row.items():
        if k == 'Geographic Area Name':
            geoname = v
        elif '!!' in k:
            parts = k.split('!!')
            parts += [''] * (6 - len(parts))
            parts = [p.rstrip(':') for p in parts]  # colon started in 2019


            data_type, _, sex, age, born, cit = parts

            if not sex:
                # top level totals
                if data_type == 'Estimate':
                    tot_est = int(v)
                elif data_type == 'Margin of Error':
                    tot_moe == int(v)

            elif age == '18 years and over' and not born:
                # totals for age range, split by sex
                if data_type == 'Estimate':
                    adu_ests.append(v)
                elif data_type == 'Margin of Error':
                    adu_moes.append(v)

            elif born == 'Native' or cit == 'Naturalized U.S. citizen':
                # citizen data
                if data_type == 'Estimate':
                    cit_ests.append(v)
                elif data_type == 'Margin of Error':
                    cit_moes.append(v)

                if age == '18 years and over':
                    if data_type == 'Estimate':
                        cvap_ests.append(v)
                    elif data_type == 'Margin of Error':
                        cvap_moes.append(v)

    return dict(
        geoname=geoname,
        geotype=geotype,
        tot_est=tot_est,
        tot_moe=tot_moe,
        adu_est=sum(adu_ests),
        adu_moe=moe_of_sum(*adu_moes),
        cit_est=sum(cit_ests),
        cit_moe=moe_of_sum(*cit_moes),
        cvap_est=sum(cvap_ests),
        cvap_moe=moe_of_sum(*cvap_moes),
    )


def felon_disf_row_to_cvap(row):
    return dict(
        geoname=row['STATE'],
        geotype='state',
        # outdated, from 2016-2020 ACS data
        cvap_est_2016_2020=row['VOTING ELIGIBLE POPULATION'],
        felon_prison_est=row['PRISON'],
        felon_disf_est=row['TOTAL'],
        # not accurate; doesn't account for non-citizen felons,
        # just dervied from TOTAL/VOTING ELIGIBLE POPULATION
        #prop_cvap_felon_disf_est=row['% DISF.'] / 100,
    )
