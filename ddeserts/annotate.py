from math import ceil

from pandas import Series
from pandas.api.types import is_integer_dtype

from .load import LN_PREFIXES
from .parse import parse_geoname
from .stats import moe_of_subpop_ratio
from .stats import moe_of_sum
from .stats import subpop_ratio


# population labels in the original data
POPS = ('adu', 'cit', 'cvap', 'tot')

RACES = tuple(sorted(
    v[:-1] for v in LN_PREFIXES.values() if v
))


def add_geo_columns(df):
    """Add the *name*, *state*, and *geotype* columns by parsing
    the *geoname* column"""
    geo_df = df['geoname'].apply(lambda g: Series(parse_geoname(g)))

    for col in ('name', 'state', 'geotype'):
        df[col] = geo_df[col]


def add_all_stat_columns(df):
    """Add all annotations other than geographic columns
    (see add_geo_columns())"""
    add_race_other_columns(df)
    add_dvap_columns(df, races=RACES + ('oth',))
    add_dis_ratio_columns(df, races=RACES + ('oth',))
    add_race_ratio_columns(df, pops=POPS + ('dvap',))


def with_columns_sorted(df):
    def sort_key(col_name):
        return (len(col_name.split('_')), col_name)

    return df.reindex(sorted(df.columns, key=sort_key), axis=1)


# stat columns. probably best not to call these individually, as they're
# sometimes order-dependent

def add_dvap_columns(df, races=()):
    """Add the *dvap_est* and *dvap_moe* columns

    DVAP stands for "disenfranchised voting-age population", in contrast
    to CVAP ("citizen voting-age population"), and is just number of adults
    (adu_est) minus CVAP (cvap_est).
    """
    df[f'dvap_est'] = (df['adu_est'] - df['cvap_est']).clip(0)
    df[f'dvap_moe'] = sum_moe_cols(df, f'adu', f'cvap')

    for r in races:
        df[f'{r}_dvap_est'] = (
            df[f'{r}_adu_est'] - df[f'{r}_cvap_est']
        ).clip(0)
        df[f'{r}_dvap_moe'] = sum_moe_cols(df, f'{r}_adu', f'{r}_cvap')


def add_dis_ratio_columns(df, races=()):
    """Add columns for % of adults disenfranchised due to citizenship
    requirements."""

    # use "any" rather than "p_dis_est" to keep all p_ columns sorted together
    df['p_any_dis_est'] = div_est_cols(df, 'dvap', 'adu')
    # we know p_adu_cvap + p_adu_dvap = 1, so use CVAP MoE because it's smaller
    df['p_any_dis_moe'] = div_moe_cols(df, 'cvap', 'adu')

    # same, but by race
    for r in races:
        df[f'p_{r}_dis_est'] = div_est_cols(df, f'{r}_dvap', f'{r}_adu')
        df[f'p_{r}_dis_moe'] = div_moe_cols(df, f'{r}_cvap', f'{r}_adu')

    return df


def add_race_other_columns(df, pops=POPS):
    """Add columns for number of people who aren't covered by the basic
    racial data (under the original data's categories, these are
    non-Hispanic people of two or more races).
    """
    for pop in pops:
        df[f'oth_{pop}_est'] = (
            df[f'{pop}_est'] -
            sum(df[f'{race}_{pop}_est'] for race in RACES)
        ).clip(0)

        df[f'oth_{pop}_moe'] = sum_moe_cols(
            df, f'{pop}', *(f'{race}_{pop}' for race in RACES)
        )


def add_race_ratio_columns(df, pops=POPS):
    """Add columns like "p_adu_his_est" 
    (estimate of % of adults that are hispanic) for each
    race (including "other") and population type
    """
    for pop in pops:
        for race in RACES:
            df[f'p_{pop}_{race}_est'] = div_est_cols(
                df, f'{race}_{pop}', f'{pop}'
            )

            df[f'p_{pop}_{race}_moe'] = div_moe_cols(
                df, f'{race}_{pop}', f'{pop}'
            )

        # other % is just one 1 minus % of each race
        df[f'p_{pop}_oth_est'] = (1 - sum(
            df[f'p_{pop}_{race}_est'] for race in RACES
        )).clip(0, 1)

        # so other MoE is just the combined MoE of % of each race
        df[f'p_{pop}_oth_moe'] = sum_moe_cols(
            df,
            *(f'p_{pop}_{race}' for race in RACES)
        )


# utilities for combining columns

def div_est_cols(df, subpop, pop):
    """Like subpop_ratio(), but operating on columns."""
    return df.apply(
        lambda r: subpop_ratio(r[f'{subpop}_est'], r[f'{pop}_est']),
        axis=1,
    ).astype('float')


def div_moe_cols(df, subpop, pop):
    """Like moe_of_subpop_ratio(), but operating on columns"""
    return df.apply(
        lambda r: moe_of_subpop_ratio(
            r[f'{subpop}_est'], r[f'{subpop}_moe'], 
            r[f'{pop}_est'], r[f'{pop}_moe'], 
        ),
        axis=1,
    ).astype('float')


# there is no sum_est_cols(); just use +, -, and sum()

def sum_moe_cols(df, *pops):
    """Like moe_of_sum(), but operating on columns.

    *pops* are the column names, without the "_moe" suffix
    (e.g 'adu', 'cvap').

    returns a Series, to use as a new column
    """
    def moe_of_row(r):
        return moe_of_sum(*(r[f'{p}_moe'] for p in pops))

    result = df.apply(moe_of_row, axis=1)

    if all(is_integer_dtype(df[f'{p}_moe']) for p in pops):
        result = result.apply(ceil).astype('int')

    return result

