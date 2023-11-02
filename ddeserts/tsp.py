"""Methods specific to data from The Sentencing Project"""
from csv import DictReader

from pandas import DataFrame

# Path to felon disenfranchisement data. Pattern can be filled with
# "all", "black", or "latinx"
FELON_DISF_PATH_PATTERN = 'data/tsp/2022-felon disenfranchisement-{0}.csv'

# % of people in prison who are non-citizens
# from Locked Out (2022), p. 12
PROP_PRISON_NON_CIT = 0.049


def load_felon_disf_data(population='all'):
    path = FELON_DISF_PATH_PATTERN.format(population)

    rows = _read_felon_disf_csv(path)
    cvap_rows = [_felon_disf_row_to_cvap(row) for row in rows]

    df = DataFrame.from_records(cvap_rows)

    return df


def _read_felon_disf_csv(path):
     with open(path, newline='', encoding='latin-1') as f:
        reader = DictReader(f)

        for row in reader:
            parsed_row = _parse_felon_disf_row(row)

            yield parsed_row


def _parse_felon_disf_row(row):
    # update this to get data types right
    row = {
        k.replace('\r', ' '): v
        for k, v in row.items()
    }

    for k, v in row.items():
        if v == '':
            row[k] = 0
        elif '.' in v:
            try:
                row[k] = float(v)
            except ValueError:
                pass
        else:
            try:
                row[k] = int(v.replace(',', ''))
            except ValueError:
                pass

    return row


def _felon_disf_row_to_cvap(row):
    """Convert felon disenfranchisement data to a format like that
    used for U.S. Census citizen voting age population data"""
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

