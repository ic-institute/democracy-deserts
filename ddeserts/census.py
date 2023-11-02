"""For U.S. Census data"""
from csv import DictReader

from pandas import DataFrame

from .stats import moe_of_sum

AGE_SEX_CIT_DATA_PATH = (
    'data/census/ACSDT1Y2022.B05003/ACSDT1Y2022.B05003-Data.csv')

def load_age_sex_cit_data():
    """Load data from the B05033 (Age, Sex, Nativity, and Citizenship)
    CSV file.

    Return it as a stream of rows
    """
    rows = _read_age_sex_cit_csv(AGE_SEX_CIT_DATA_PATH)
    cvap_rows = [_age_sex_cit_row_to_cvap(row) for row in rows]

    df = DataFrame.from_records(cvap_rows)

    # fix data types
    df['tot_moe'] = df['tot_moe'].astype('int')
    df['adu_moe'] = df['adu_moe'].astype('int')
    df['cvap_moe'] = df['cvap_moe'].astype('int')
    df['cit_moe'] = df['cit_moe'].astype('int')

    return df


def _read_age_sex_cit_csv(path):

    with open(path, newline='', encoding='latin-1') as f:

        f.readline()  # skip the first line

        reader = DictReader(f)

        for row in reader:
            parsed_row = _parse_age_sex_cit_row(row)

            yield parsed_row


def _parse_age_sex_cit_row(row):
    for k, v in row.items():
        if v == 'null':
            row[k] = None
        elif v == '*****':
            row[k] = 0  # exact value, no MoE
        elif k.startswith('Estimate!!') or k.startswith('Margin of Error!!'):
            row[k] = int(v)

    return row


def _age_sex_cit_row_to_cvap(row):
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


