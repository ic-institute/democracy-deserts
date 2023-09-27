from math import ceil

from pandas import Series
from pandas.api.types import is_integer_dtype

from .parse import parse_geoname
from .stats import est_of_prop
from .stats import moe_of_prop
from .stats import moe_of_sum


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
    # these will be consolidated into 'tmr_'
    'American Indian or Alaska Native and White': 'tiw_',
    'Asian and White': 'taw_',
    'Black or African American and White': 'tbw_',
    'American Indian or Alaska Native and Black or African American': 'tib_',
    'Remainder of Two or More Race Responses': 'trm_',
}


# population labels in the original data
POPS = ('adu', 'cit', 'cvap', 'tot')

# racial ethnic/groups we collect data for
RACES = ('asn', 'blk', 'his', 'ind', 'pac', 'wht', 'tmr')


def add_geo_columns(df):
    """Add the *name*, *state*, and *geotype* columns by parsing
    the *geoname* column"""
    geo_df = df['geoname'].apply(lambda g: Series(parse_geoname(g)))

    for col in ('name', 'state', 'geotype'):
        df[col] = geo_df[col]


def add_all_stat_columns(df):
    """Add all annotations other than geographic columns
    (see add_geo_columns())"""
    consolidate_two_or_more_race_columns(df)
    add_dvap_columns(df)
    add_dis_prop_columns(df)
    add_race_prop_columns(df)
    add_racial_disp_cols(df)
    #add_racial_disp_score_cols(df)


def with_columns_sorted(df):
    def sort_key(col_name):
        return (len(col_name.split('_')), col_name)

    return df.reindex(sorted(df.columns, key=sort_key), axis=1)


# stat columns. probably best not to call these individually, as they're
# sometimes order-dependent

def consolidate_two_or_more_race_columns(df):
    """Consolidate the various two-or-more race columns into "tmr"
    (two or more races) columns."""
    ln_races = {r.rstrip('_') for r in LN_PREFIXES.values() if r}
    # subgroups to consolidated into "tmr" (two or more races)
    tmr_races = sorted(ln_races - set(RACES))

    for pop in POPS:
        df[f'tmr_{pop}_est'] = sum(
            df[f'{r}_{pop}_est'] for r in tmr_races)

        df.drop(
            [f'{r}_{pop}_est' for r in tmr_races],
            axis=1, inplace=True,
        )

        df[f'tmr_{pop}_moe'] = sum_moes(
            df, *(f'{r}_{pop}' for r in tmr_races)
        )

        df.drop(
            [f'{r}_{pop}_moe' for r in tmr_races],
            axis=1, inplace=True,
        )


def add_dvap_columns(df):
    """Add the *dvap_est* and *dvap_moe* columns

    DVAP stands for "disenfranchised voting-age population", in contrast
    to CVAP ("citizen voting-age population"), and is just number of adults
    (adu_est) minus CVAP (cvap_est).
    """
    df['dvap_est'] = (df['adu_est'] - df['cvap_est']).clip(0)
    df['dvap_moe'] = sum_moes(df, 'adu', 'cvap')

    for r in RACES:
        df[f'{r}_dvap_est'] = (
            df[f'{r}_adu_est'] - df[f'{r}_cvap_est']
        ).clip(0)
        df[f'{r}_dvap_moe'] = sum_moes(df, f'{r}_adu', f'{r}_cvap')


def add_dis_prop_columns(df):
    """Add columns for % of adults disenfranchised due to citizenship
    requirements."""

    df['prop_adu_dvap_est'] = prop_ests(df, 'dvap', 'adu')
    # we know p_adu_cvap + p_adu_dvap = 1, so use CVAP MoE because it's smaller
    df['prop_adu_dvap_moe'] = prop_moes(df, 'cvap', 'adu')

    # same, but by race
    for r in RACES:
        df[f'prop_{r}_adu_dvap_est'] = prop_ests(df, f'{r}_dvap', f'{r}_adu')
        df[f'prop_{r}_adu_dvap_moe'] = prop_moes(df, f'{r}_cvap', f'{r}_adu')

    return df


def add_race_prop_columns(df):
    """Add columns like "prop_adu_his_est" 
    (estimate of % of adults that are hispanic) for each
    racial/ethnic group
    """
    for pop in POPS + ('dvap',):
        for race in RACES:
            df[f'prop_{pop}_{race}_est'] = prop_ests(
                df, f'{race}_{pop}', f'{pop}'
            )

            df[f'prop_{pop}_{race}_moe'] = prop_moes(
                df, f'{race}_{pop}', f'{pop}'
            )


def add_racial_disp_cols(df):
    for r in RACES:
        df[f'racial_disp_{r}_est'] = (
            df[f'prop_cvap_{r}_est'] - df[f'prop_adu_{r}_est']
        )

        df[f'racial_disp_{r}_moe'] = sum_moes(
            df, f'prop_cvap_{r}', f'prop_adu_{r}'
        )


def add_racial_disp_score_cols(df):
    def make_score_cols(row):
        ests = []
        moes = []

        for race in RACES:
            if race == 'tmr':
                # don't include two-or-more-races catchall in score
                continue

            est = row[f'racial_disp_{race}_est']
            moe = row[f'racial_disp_{race}_moe']

            if est < 0:
                # race is undrerrepresented
                ests.append(est)
                moes.append(moe)
            elif est - moe < 0:
                # race is estimated to be over-represented, but might 
                # actually be under-represented by a bit because of MoE
                moes.append(moe - est)

        return Series([-sum(ests) * 100, moe_of_sum(*moes) * 100])

    score_df = df.apply(make_score_cols, axis=1)
    df[['racial_disp_score_est', 'racial_disp_score_moe']] = score_df


# utilities for combining columns

def prop_ests(df, subpop, pop):
    """Like est_of_prop(), but operating on columns."""
    return df.apply(
        lambda r: est_of_prop(r[f'{subpop}_est'], r[f'{pop}_est']),
        axis=1,
    ).astype('float')


def prop_moes(df, subpop, pop):
    """Like moe_of_prop(), but operating on columns"""
    return df.apply(
        lambda r: moe_of_prop(
            r[f'{subpop}_est'], r[f'{pop}_est'],
            r[f'{subpop}_moe'], r[f'{pop}_moe'],
        ),
        axis=1,
    ).astype('float')


# there is no sum_ests(); just use +, -, and sum()

def sum_moes(df, *pops):
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

