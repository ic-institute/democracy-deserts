from math import ceil

from pandas import Series

from .parse import parse_geoname
from .stats import moe_of_subpop_ratio
from .stats import moe_of_sum
from .stats import subpop_ratio


def add_dvap_columns(df):
    """Add the *dvap_est* and *dvap_moe* columns

    DVAP stands for "disenfranchised voting-age population", in contrast
    to CVAP ("citizen voting-age population"), and is just number of adults
    (adu_est) minus CVAP (cvap_est).
    """
    df['dvap_est'] = df['adu_est'] - df['cvap_est']
    df['dvap_moe'] = df.apply(
        lambda r: (
            ceil(moe_of_sum(r['adu_moe'], r['cvap_moe']))
        ),
        axis=1
    ).astype('int')

    # add p_adu_dvap_{est,moe}
    add_ratio_columns(df, 'dvap', 'adu')

    return df


def add_geo_columns(df):
    """Add the *name*, *state*, and *geotype* columns by parsing
    the *geoname* column"""
    geo_df = df['geoname'].apply(lambda g: Series(parse_geoname(g)))

    for col in ('name', 'state', 'geotype'):
        df[col] = geo_df[col]


def add_has_charter_column(df, charter_cities):
    """Add the *charter_cities* column, based on *name* and *geotype*;
    these fields are added by add_geo_columns()
    """
    df['has_charter'] = (
        df['name'].isin(charter_cities) & df['geotype'] == 'city'
    )

    return df


def add_ratio_columns(df, subpop, pop, name=None):
    if name is None:
        # e.g. his_adu_est, adu_est -> adu_his
        name = pop.split('_')[0] + '_' + subpop.split('_')[0]

    df[f'p_{name}_est'] = df.apply(
        lambda r: subpop_ratio(r[f'{subpop}_est'], r[f'{pop}_est']),
        axis=1,
    ).astype('float')

    df[f'p_{name}_moe'] = df.apply(
        lambda r: moe_of_subpop_ratio(
            r[f'{subpop}_est'], r[f'{subpop}_moe'], 
            r[f'{pop}_est'], r[f'{pop}_moe'], 
        ),
        axis=1,
    ).astype('float')