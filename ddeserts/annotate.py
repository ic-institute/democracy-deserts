from math import ceil

from pandas import Series

from .load import LN_PREFIXES
from .parse import parse_geoname
from .stats import moe_of_subpop_ratio
from .stats import moe_of_sum
from .stats import subpop_ratio

RACES = sorted(
    v[:-1] for v in LN_PREFIXES.values() if v
)


def add_all_stat_columns(df):
    """Add all annotations other than geographic columns
    (see add_geo_columns(), add_charter_column())."""
    add_race_other_columns(df)
    add_dvap_columns(df)


def add_dvap_columns(df):
    """Add the *dvap_est* and *dvap_moe* columns

    DVAP stands for "disenfranchised voting-age population", in contrast
    to CVAP ("citizen voting-age population"), and is just number of adults
    (adu_est) minus CVAP (cvap_est).
    """
    df['dvap_est'] = df['adu_est'] - df['cvap_est']
    df['dvap_moe'] = sum_moe_cols(df, 'adu', 'cvap')

    # add p_adu_dvap_{est,moe}
    add_ratio_columns(df, 'dvap', 'adu')

    return df


def add_geo_columns(df):
    """Add the *name*, *state*, and *geotype* columns by parsing
    the *geoname* column"""
    geo_df = df['geoname'].apply(lambda g: Series(parse_geoname(g)))

    for col in ('name', 'state', 'geotype'):
        df[col] = geo_df[col]


def add_charter_column(df, charter_cities):
    """Add the *charter_cities* column, based on *name* and *geotype*;
    these fields are added by add_geo_columns()
    """
    df['charter'] = (
        df['name'].isin(charter_cities) & df['geotype'] == 'city'
    )


def add_race_other_columns(df):
    """Add columns for number of people who aren't covered by the basic
    racial data (under the original data's categories, these are
    non-Hispanic people of two or more races).
    """
    for pop in ('adu', 'cit', 'cvap', 'tot'):
        df[f'oth_{pop}_est'] = (
            df[f'{pop}_est'] -
            sum(df[f'{race}_{pop}_est'] for race in RACES)
        )

        df[f'oth_{pop}_moe'] = sum_moe_cols(
            df, f'{pop}', *(f'{race}_{pop}' for race in RACES)
        )


def add_ratio_columns(df, subpop, pop, name=None):
    if name is None:
        # e.g. his_adu_est, adu_est -> adu_his
        name = pop.split('_')[0] + '_' + subpop.split('_')[0]

    df[f'p_{name}_est'] = div_est_cols(df, subpop, pop)
    df[f'p_{name}_moe'] = div_moe_cols(df, subpop, pop)


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

def sum_moe_cols(df, *pops, to_int=True):
    """Like moe_of_sum(), but operating on columns.

    *pops* are the column names, without the "_moe" suffix
    (e.g 'adu', 'cvap').

    returns a Series, to use as a new column
    """
    def moe_of_row(r):
        return moe_of_sum(*(r[f'{p}_moe'] for p in pops))

    result = df.apply(moe_of_row, axis=1)

    if to_int:
        result = result.apply(ceil).astype('int')

    return result


def with_columns_sorted(df):
    def sort_key(col_name):
        return (len(col_name.split('_')), col_name)

    return df.reindex(sorted(df.columns, key=sort_key), axis=1)
