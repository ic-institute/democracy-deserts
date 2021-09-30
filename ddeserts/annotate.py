from math import ceil

from .stats import moe_of_ratio
from .stats import moe_of_sum


def add_dvap_columns(df):
    df['dvap_est'] = df['adu_est'] - df['cvap_est']
    df['dvap_moe'] = df.apply(
        lambda r: (
            ceil(moe_of_sum(r['adu_moe'], r['cvap_moe']))
        ),
        axis=1
    ).astype('int')

    df['dvap_pct'] = df['dvap_est'] / df['adu_est']
    df['dvap_pct_moe'] = df.apply(
        lambda r: moe_of_ratio(
            r['dvap_est'], r['dvap_moe'], r['adu_est'], r['adu_moe']
        ),
        axis=1
    ).astype('float')

    return df


def add_has_charter_column(df, charter_cities):
    df['has_charter'] = df['name'].isin(charter_cities)

    return df