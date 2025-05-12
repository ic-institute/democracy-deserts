"""Statistics, mostly for calculating margin of error.

Derived from the ACS General Handbook (see
data/census/acs_general_handbook_2018_ch08.pdf)
"""
from numpy import NaN
from numpy import isnan
from math import sqrt


def moe_of_sum(*moes):
    """Combine margin of error of two or more independent distributions
    using sum of squares. Works for sums or differences.
    """
    return sqrt(sum(moe ** 2 for moe in moes))


def moe_of_product(x_est, y_est, x_moe, y_moe):
    """Approximate error of a product"""
    return sqrt((x_est * y_moe) ** 2 + (y_est * x_moe) ** 2)


def moe_of_prop(subpop_est, pop_est, subpop_moe, pop_moe):
    """Approximate margin of error for the ratio of a subpopulation size
    to the population size, assuming these estimates were made from
    different sources (as happens in ACS data).
    """    
    prop = est_of_prop(subpop_est, pop_est)

    if isnan(prop) or not pop_est >= 0:
        return NaN

    # this is the "ratio" estimate from the ACS General Handbook; the tighter
    # "proportion" method only works when the population MoE is constructed
    # from the subpopulation MoE, which isn't the case in this dataset
    moe = 1 / pop_est * sqrt(
        subpop_moe ** 2 + (prop * pop_moe) ** 2
    )

    # actual value has to be between 0 and 1, limiting MoE
    max_moe = max(1 - prop, prop)

    return min(max_moe, moe)


def est_of_prop(subpop_est, pop_est):
    """Basically subpop_est divided by pop_est, but with the final
    value clamped between 0 and 1. If pop_est is 0, returns pd.NA.
    """
    if not pop_est > 0:
        return NaN

    return min(max(subpop_est / pop_est, 0), 1)